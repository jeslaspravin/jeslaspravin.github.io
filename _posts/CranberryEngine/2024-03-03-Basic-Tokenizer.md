---
layout: single
title:  "Basic tokenizer"
date:   2024-03-03
mathjax: false
categories: 
    - cranberry
header:
    teaser: /assets/images/CranberryEngine/compiler_tokenizer_cartoon.jpg
---
## Basic tokens parser

The tokenizer that I am about to create will contained inside a parser helper class. This is the first version of general purpose tokenizer.
It is created to allow parsing my custom text based config format. So first I will specify the semantics of the config language.

### CBE Config language

The language takes inspiration from `JSON` but instead of having arrays and objects. This one will have only scopes semantically. However the data itself must allow storing arrays, it is achieved using `+` and `-`. The language also allows copying values from another scope it can be achieved by using evaluated assignment `:=` of any value, list indexing must be allowed when copying.

There is also another difference instead of using `.` separator for scopes, This language will use `/` like path separator.

Example

```ini
# Comment

# All of the below are in root scope("/")
strVar="Something"
iVar=234
strVar="Overwrite"
fVar=123.456
listVar+=234 # = is a token so does the + or - before that
listVar+=-123
listVar-=-123 # Removes -123

# Scope can be started using either scope header or using implicit scopes {}

# Explicit scope, explicit scope cannot be used to append or remove from list.
[/scopeOuter]
aVar="Something"
lVar+="Something something"
lVar+="Another thing"

[/scopeOuter/innerObj0]
sVar="Something"
sListVar+="Something something"
sListVar+="Another thing"

[/scopeOuter/innerObj1]
sVar="Something new"
sListVar+="Something something new"
sListVar+="Another new thing"

# However one can directly inline initialize into list like below. Be aware it will create continuous array not sparse array, Assigning to some 100th index creates array with 100 elements.
[/scopeOuter/innerList/0]
sVar="Something element 0"
sListVar+="Something something"
sListVar+="Another thing"

[/scopeOuter/innerList/1]
sVar="Something new element 1"
sListVar+="Something something new"
sListVar+="Another new thing"

# Above scopes can also be made using implicit blocks
scopeOuter1={
    aVar="Something"
    lVar+="Something something"
    lVar+="Another thing"
    innerObj0={
        sVar="Something"
        sListVar+="Something something"
        sListVar+="Another thing"
    }
    innerObj1={
        sVar="Something new"
        sListVar+="Something something new"
        sListVar+="Another new thing"
    }
    innerList+={
        sVar="Something element 0"
        sListVar+="Something something"
        sListVar+="Another thing"
    }
    innerList+={
        sVar="Something new element 1"
        sListVar+="Something something new"
        sListVar+="Another new thing"
    }
}

copyVar:=/scopeOuter/aVar # Copy assignment
copyList+:=/strVar # Copy followed by add
copyList+:=/scopeOuter1/innerList/0 # Copy from a list element
copyList+:=/scopeOuter1/innerList # Append entire list

```

From the example there are following basic tokens

- Assignment token
  - `=`
  - Assigns the value in the right to variable in the left
- Copy assign from token
  - `:=`
  - Copies the values from from variable path in right side to the variable in the left
- Add token
  - `+`
  - Adds something to something. In our case it will be list element from value or copy
- Remove token
  - `-`
  - Removes something from something. In our case it will be list element from value or copy
- Qoute token
  - `"` or `'`
  - Useful to specify space include multiline characters
- Escape character token
  - `\`
  - Useful to skip special charater sequence
- New line token
  - `\r?\n`
  - Matches each new line
- Scope decl start and end tokens
  - `[` and `]` respectively
  - In our case used to start a scope section. End when a new section starts
- Scope separator token
  - `/`
- Scope section start and end tokens
  - `{` and `}` respectively
  - Encapsulate a scope section

Additional tokens like variable names, text concat across lines can be obtained from second semantic token pass.

- Variable assignment semantics
  - Regex pattern `R'^[a-zA-Z_]{1}[a-zA-Z0-9_]*'`
  - `Regex` [`Assignment`, `Copy Assignment`] [`R'.*'`, `Open section`]
  - `Regex` [`Add`, `Remove`] [`Assignment`, `Copy Assignment`] [`R'.*'`, `Open section`]
- Text concat
  - `'\\'` `New Line`
- Variable use
  - Regex pattern `R'^[a-zA-Z_]{1}[a-zA-Z0-9_]*'`
  - `Scope decl start` (`Scope seperator` `Regex`)+ `Scope decl end` So the semantic tokenizer must have ability to do sub expression matching.
  - `Regex` `Copy Assignment` (`Scope seperator` `Regex`)+
  - `Regex` [`Add`, `Remove`] `Copy Assignment` (`Scope seperator` `Regex`)+
  
Third pass is scoping pass where all the scopes are validated.
In our case there are only three scopes

- Scope decl `[...]`
- Scope section `{...}`
- Text `"..."` `'...'`

This pass must receive the entire list of scope tokens, validates the scopes.

The fourth pass is verifying the semantic's gramatical correctness. This involves checking if each sentence or semantic is matching one of the grammer provided. If it does not match the closest matching grammer and range must be returned with result. This is necessary for clear error reporting.

This example is very simple so the list of grammers are

- Scope section start declaration
  - `Scope decl start` `Variable use` `Scope decl end`
- Variable assignment
  - Regex pattern `R'^[a-zA-Z_]{1}[a-zA-Z0-9_]*'`
  - `Regex` [`Assignment`, `Copy Assignment`] [[(`R'.*'` `Escape character` `New line`), (`R'.*'` `New line`) ], `Open section`]
  - `Regex` [`Add`, `Remove`] [`Assignment`, `Copy Assignment`] [[(`R'.*'` `Escape character` `New line`), (`R'.*'` `New line`) ], `Open section`]

## Defining the requirement for the helpers

- The parser helper will only work with `StringView`. Do not modify the source itself.
- Basic tokenizer is simple receives a bunch of `token characters` or `regex` or `token strings`. All case sensitive. Tokenizes the StringView and constructs a linear array of results ordered in same order the tokens appear in source string.
- Semantic tokenizer starts to get complex. It receives a bunch of semantics that contains list of tokens, regexes and sub semantics(Like sub expressions in regex). All the marked regexes of the non tokenized region gets tokenized here.
- Scope validation checks all the scope able tokens and ensure that they are valid pairs.
- Scoping pass groups all the tokens into its corresponding scoping region. Works with array ranges(Not `std::ranges`).
- Grammer check pass receive bunch of regexes and tokens like semantic tokenizer, checks the grammatical correctness.
- Additional getters and setters to get the data needed from parsed outputs.

### Pass 1 - Basic tokens

Basic tokens just need to know the input `StringView`. List of tokens, its type and pattern to match.
The structure might look like. The output will be list of `ParseTokens`

```cpp
using TokenType = uint32;

enum class ETokenPatternType : uint8
{
    CharMatch,
    StringMatch,
    Regex,
    /* Below types are used only from semantics tokenizer only */
    Token,
    Subexpression,
};

struct TokenizerPattern
{
    union Pattern
    {
        TChar charMatch;
        String strMatch;
        const StringRegex *regex;
        ArrayView<TokenizerPattern> subExps;
        TokenType tokenType;
    };

    ETokenPatternType type;
    Pattern pattern;

    int32 minCount = 1;
    int32 maxCount = 1;
    /* Should match any number of times, maxCount will be ignored */
    bool bMany:1 = false;
    bool bIgnoreSpaces:1 = true;
};

struct BasicToken
{
    TokenType tokenType;
    TokenizerPattern pattern;
};

/* Output token after parsing */
struct ParsedTokens
{
    StringView view;
    TokenType tokenType;
    ETokenPatternType matchedType;
    TokenizerPattern::Pattern matchPattern;
};
```

### Pass 2 - Semantic tokens

This pass requires the previously created list of `ParsedTokens` as input and output. Input is list of grammar as list of `SemanticSentance`. Both subexpressions and token patterns are supported in addition to other pattern types.

```cpp
struct SemanticToken
{
    TokenizerPattern aWord;
    /* Token to assign if this pattern matches */
    TokenType tokenType;
    /* Should assign token */
    bool bAssignToken:1 = false;
};

struct SemanticSentance
{
    ArrayView<SemanticToken> words;
};
```

### Pass 3 - Scope validation

Receives list of scope tokens and validates if the scopes are complete. Input must be list of `ParsedTokens` and list of `ScopeTokens`. The errors are returned in list of `ParseError`.

```cpp
struct ScopeTokens
{
    TokenType startToken;
    TokenType endToken;
};

struct ParseError
{
    String errorStr;
    SizeT errorAt;
    uint32 line;
    uint32 column;
};
```

### Pass 4 - Scoping the tokens

Receives list of scope tokens similar to pass 3 and groups the subtokens into it. Input must be list of `ParsedTokens` and list of `ScopeTokens`. The errors are returned in list of `ParseError`. Also returns list of `TokensGroup` which contains the `ParsedTokens` range which are inside a scope.
This functionality could be combined with Pass 3 to group conditionally.

```cpp
struct TokensGroup
{
    /* Begin scope token index, index of startToken */ 
    uint32 beginTokenIdx;
    /* End scope token index, index of endToken */
    uint32 endTokenIdx;
    TokenType startToken;
    TokenType endToken;
    /* Inclusize range of tokens that belong to this group.
     * To get the StringView range use beginTokenIdx's end to endTokenIdx's begin. */
    ValueRange<uint32> scopeRange;
};
```

### Pass 5 - Grammer check

Checks the grammatical correctness and returns the errors if any as list of `ParseError`. Input is list of `SentenceGrammar`, `ParsedTokens` and `TokensGroup`. Also returns list of `GrammarMatchesPerGroup` for each `SentenceGrammar` inside each group.

```cpp
struct WordGrammar
{    
    TokenizerPattern aWord;
    bool bCapture:1 = false;
};

struct SentenceGrammar
{
    ArrayView<WordGrammar> words;
};

struct GrammarMatchesPerSentence
{
    /* All matches per sentence for each matched sentences.
     * If 20 sentences matches at capturing 2 per sentence then size will be 40 */
    std::vector<StringView> matches;
};
struct GrammarMatchesPerGroup
{
    std::vector<GrammarMatchesPerSentence> matches;
};
```

## End note

I hope the above design is enough to get my config language parsed using my general purpose parser helpers.

[//]: # (Below are link reference definitions)
