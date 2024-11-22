---
layout: single
title:  "Basic tokenizer"
date:   2024-03-03
mathjax: false
categories: 
    - cranberry
header:
    teaser: /assets/images/CranberryEngine/compiler_tokenizer_cartoon.jpg
sidebar:
    nav: "Cranberry"
---
## Basic tokens parser

The tokenizer I’m about to create will be contained within a parser helper class. This initial version serves as a general-purpose tokenizer and is designed to parse my custom text-based configuration format. Let’s start by specifying the semantics of the config language.

### CBE Config language

The language draws inspiration from `JSON`, but instead of using arrays and objects, it focuses solely on scopes. These scopes carry semantic meaning within the configuration. Although the language doesn’t directly support arrays, it allows for array-like behavior by using `+` and `-` symbols.

- Scopes and Semantics:
  - Unlike `JSON`, which has arrays and objects, the language focuses solely on scopes.
  - These scopes carry semantic meaning within the configuration.
  - The absence of arrays and objects simplifies the structure.
- Data Storage with Arrays:
  - While the language doesn't directly support arrays, It enables array-like behavior using `+` and `-`.
  - This allows for efficient parsing of data.
- Copying Values:
  - The ability to copy values from one scope to another is a powerful feature.
  - It is achieved through evaluated assignment (`:=`).
  - It's like creating references or aliases to existing data.
- Path Separators:
  - Instead of the common `.` separator for scopes, the language opts for `/`.
  - This choice aligns with path-like semantics, making it intuitive for users.

Example

```ini
# Comment

# All of the below are in root scope("/")
strVar="Something" # Testing after the string
iVar=234
strVar=Overwrite # Testing after the unquoted string
fVar=123.456
listVar+=234 # = is a token so does the + or - before that
listVar+=-123
listVar-=-123 # Removes -123
strFVar="123.456"# Number inside quote
# Multiline string
mStrDQ="""Multiline
string
using 
double
quote
"""
mStrSQ='''Multiline
string
using 
single
quote
'''

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

{: .emphasis}
From the example these are the basic tokens

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
- Quote token
  - `"` or `'`
  - Useful to specify space in string value
- Multiline string quote token
  - `"""` or `'''`
  - Useful to write multiline string
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

{: .emphasis}
During the second semantic token pass, additional tokens such as variable names, text concatenation across lines, multiline string values, and numbers can be extracted.

- Variable assignment semantics
  - Regex pattern `R'^[a-zA-Z_]{1}[a-zA-Z0-9_]*'`
  - `Regex` [`Assignment`, `Copy Assignment`] [`R'.*'`, `Open section`]
  - `Regex` [`Add`, `Remove`] [`Assignment`, `Copy Assignment`] [`R'.*'`, `Open section`]
- Variable use
  - Regex pattern `R'^[a-zA-Z_]{1}[a-zA-Z0-9_]*'`
  - `Scope decl start` (`Scope seperator` `Regex`)+ `Scope decl end` So the semantic tokenizer must have ability to do sub expression matching.
  - `Regex` `Copy Assignment` (`Scope seperator` `Regex`)+
  - `Regex` [`Add`, `Remove`] `Copy Assignment` (`Scope seperator` `Regex`)+
- Variable use with index
  - Regex pattern `R'^[a-zA-Z_]{1}[a-zA-Z0-9_]*'`
  - RegexIdx pattern `R"\d+"`
  - `Scope decl start` (`Scope seperator` `Regex`)+ `Scope seperator` `RegexIdx` `Scope decl end` So the semantic tokenizer must have ability to do sub expression matching.
  - `Regex` `Copy Assignment` (`Scope seperator` `Regex`)+ `Scope seperator` `RegexIdx`
  - `Regex` [`Add`, `Remove`] `Copy Assignment` (`Scope seperator` `Regex`)+ `Scope seperator` `RegexIdx`
- Comment string
  - Regex pattern `R".*"` to match anything after comment token until EOL or EOF.
  - `Comment` `Regex` [`Line feed`, `EOF`]
- String value
  - Regex `R"[^\s#]+"` match anything but comment or spaces.
  - RegexQuoted `R"['"](.+)['"]"` match anything enclosed inside quotes as string but single line.
  - RegexMultiline `R"[\s\S]*?"` everything both space and non space characters.
  - `VarName` `Assignment` [ `Regex` `RegexQuoted` `RegexNumber` `Section start` ]
  - `VarName` [`Add`, `Remove`] `Assignment` [ `Regex` `RegexQuoted` `RegexNumber` `Section start` ]
  - `VarName` `Assignment` `Multiline Quote` `RegexMultiline` `Multiline Quote`
  - `VarName` [`Add`, `Remove`] `Assignment` `Multiline Quote` `RegexMultiline` `Multiline Quote`
- Number value
  - Regex `R"[-+]?\d*[.]?\d+"`
  - `VarName` `Assignment` `Regex`
  - `VarName` [`Add`, `Remove`] `Assignment` `Regex`

{: .emphasis}  
The third pass involves a scoping check, where all the scopes are validated.

In our case there are only three scopes

- Scope decl `[...]`
- Scope section `{...}`
- Text `"..."` `'...'`

This pass must receive the entire list of scope tokens, validate the scopes.

{: .emphasis}
The fourth step involves verifying the semantic and grammatical correctness. During this phase, we check whether each sentence or semantic aligns with the provided grammar. If it does not match the closest matching grammar, we return the relevant range along with the result. This step is crucial for clear error reporting.

This example is very simple so the list of grammers are

- Scope section start declaration
  - `Scope decl start` `Variable use` `Scope decl end`
- Variable assignment
  - Regex pattern `R'^[a-zA-Z_]{1}[a-zA-Z0-9_]*'`
  - `Regex` [`Assignment`, `Copy Assignment`] [[(`R'.*'` `Escape character` `New line`), (`R'.*'` `New line`) ], `Open section`]
  - `Regex` [`Add`, `Remove`] [`Assignment`, `Copy Assignment`] [[(`R'.*'` `Escape character` `New line`), (`R'.*'` `New line`) ], `Open section`]

## Defining the requirement for the helpers

1. **Parser Helper**:
   - The parser helper exclusively works with `StringView`. It's essential to avoid modifying the source itself.

2. **Basic Tokenizer**:
   - The basic tokenizer is straightforward. It receives a set of inputs, which can be either:
     - `token characters`
     - `regex`
     - `token strings`
   - All of these are case-sensitive. The tokenizer processes the `StringView` and constructs a linear array of results, maintaining the order in which the tokens appear in the source string.

3. **Semantic Tokenizer**:
   - The semantic tokenizer introduces complexity. It receives a collection of semantics, each containing:
     - A list of tokens
     - Regular expressions (regexes)
     - Sub-semantics (similar to sub-expressions in regex)
   - Notably, it tokenizes the marked regexes within non-tokenized regions.

4. **Scope Validation**:
   - This step checks all scope-able tokens to ensure they form valid pairs.

5. **Scoping Pass**:
   - During the scoping pass, tokens are grouped into their corresponding scoping regions. This process operates with array ranges (not `std::ranges`).

6. **Grammar Check Pass**:
   - Similar to the semantic tokenizer, the grammar check pass receives a set of regexes and tokens. Its purpose is to verify grammatical correctness.

7. **Additional Getters and Setters**:
   - These functions allow retrieval of necessary data from the parsed outputs.

### Pass 1 - Basic tokens

**Basic tokens** simply require knowledge of the input `StringView`. You provide a list of tokens, along with their type and matching pattern. The resulting structure might resemble the following, yielding a list of `ParseTokens`.

```cpp
using TokenType = uint32;

enum class ETokenPatternType : uint8
{
    Invalid,
    CharMatch,
    StringMatch,
    Regex,
    /* Below types are used only from semantics tokenizer only */
    Token,
    Subexpression,
    /* End of file only matches the end */
    Eof,
};

struct TokenizerPattern
{
    union Pattern
    {
        TChar charMatch;
        StringView strMatch;
        const StringRegex *re;
        ArrayView<TokenizerPattern> subExps;
        TokenType tokenType;
    };

    ETokenPatternType type = ETokenPatternType::Invalid;
    Pattern pattern = MakeTokenizerPattern<ETokenPatternType::Invalid>::make<Pattern>();

    int32 minCount = 1;
    int32 maxCount = 1;
    /* Should match any number of times, maxCount will be ignored */
    bool bMany:1 = false;
    bool bIgnoreSpaces:1 = true;
};

struct BasicTokenDesc
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

This step relies on the **previously generated list of `ParsedTokens`** as both input and output. The input consists of a grammar list represented by a collection of `SemanticSentences`. Notably, this grammar supports various elements, including subexpressions, token patterns, and other pattern types.

```cpp
struct SemanticTokenDesc
{
    TokenizerPattern aWord;
    /* Token to assign if this pattern matches */
    TokenType tokenType = 0;
    /* Should assign token */
    bool bAssignToken:1 = false;
};

struct SemanticSentenceDesc
{
    ArrayView<SemanticTokenDesc> words;
};
```

### Pass 3 - Scope validation

This step **validates the completeness of scope tokens**. The input consists of a list of `ParsedTokens` and a list of `ScopeTokens`. Any errors encountered during validation are returned as a list of `ParseError` objects.

```cpp
struct ScopeTokenDesc
{
    TokenType startToken;
    TokenType endToken;
    bool bAllowNesting:1;
};

struct ParseError
{
    /* Every string view from startToken.view.begin() to endToken.view.end() was probably matched */
    TokenIndex startToken;
    TokenIndex endToken;
    /* Additional error string */
    String errorStr;
    SizeT errorAt;
    uint32 line;
    uint32 column;
};
```

### Pass 4 - Scoping the tokens

This function takes in a list of scope tokens, similar to pass 3. It then groups the subtokens within those scopes. The input consists of two lists: one containing `ParsedTokens` and the other containing `ScopeTokens`. Any errors encountered during this process are returned as a list of `ParseError`. Additionally, the function returns a list of `TokensGroup`, which contains the ranges of `ParsedTokens` that fall within a specific scope. This functionality can be combined with Pass 3 to conditionally group tokens.

```cpp
struct TokensGroup
{
    /* Begin scope token index, index of startToken */
    TokenIndex beginTokenIdx;
    /* End scope token index, index of endToken */
    TokenIndex endTokenIdx;
    TokenType startToken;
    TokenType endToken;
    ValueRange<TokenIndex> scopeRange;
};
```

### Pass 5 - Grammer check

This function **verifies the grammatical correctness** and identifies any errors. It takes as input a list of `SentenceGrammar`, `ParsedTokens`, and `TokensGroup`. Additionally, it returns a list of `GrammarMatchesPerGroup` for each `SentenceGrammar` within each group.

```cpp
struct WordGrammarDesc
{
    TokenizerPattern aWord;
    bool bCapture:1 = false;
};

struct SentenceGrammarDesc
{
    ArrayView<WordGrammarDesc> words;
};

struct GrammarMatchesPerSentence
{
    /* All matches per sentence for each matched sentences.
     * If 20 sentences matches at capturing 2 per sentence then size will be 40 */
    ArrayRange<StringView> matches;
};
struct GrammarMatchesPerGroup
{
    ArrayRange<GrammarMatchesPerSentence> matches;
};
```

### Helpers

While contemplating all conceivable combinations of sentence semantics, I swiftly recognized the necessity for an improved approach. Consequently, I devised the following helper functions to handle these combinations. Notably, the code generation and data population occurs during compile time. I have also added a few combinations of the `fillCombinations` and `createCombinations` functions to work with dynamic and static data.

```cpp
/**
* The elements in an array gets distributed from first to last. So the one in lesser index gets checked first when parsing.
* Uses plain array or std::array as input combos and returns std::array.
* Meant to be used to generate combinations entirely at compile time.
*/
template <ConstSizeArray... TCombos>
constexpr static auto createCombinations(TCombos &&...combos)
{
    constexpr SizeT EXTENT = COMBO_EXTENT<TCombos...>;
    constexpr SizeT RANK = COMBO_RANK<TCombos...>;
    using Type = ComboHelper<std::remove_cvref_t<TCombos>...>::type;

    std::array<std::array<Type, RANK>, EXTENT> outArr;
    for (SizeT i = 0; i < EXTENT; ++i)
    {
        outArr[i]
            = createCombosArray<decltype(outArr)::value_type>(std::index_sequence_for<TCombos...>{}, i, std::forward<TCombos>(combos)...);
    }
    return outArr;
}

template <ConstSizeArray T, SizeT... idxs, ConstSizeArray... TCombos>
constexpr static T createCombosArray(std::index_sequence<idxs...>, SizeT comboId, TCombos &&...combos)
{
    constexpr SizeT EXTENT = ComboHelper<T>::extent;
    static_assert(sizeof...(combos) == sizeof...(idxs) && sizeof...(combos) == EXTENT, "Something is VERY wrong!");
    SizeT comboIds[EXTENT] = { ComboHelper<std::remove_cvref_t<TCombos>>::extent... };
    /* Since left most must be the largest rank and varying slowly. This order keeps the similar matches grouped together */
    for (int64 i = 0; i < EXTENT; ++i)
    {
        SizeT stride = 1;
        for (int64 ii = i + 1; ii < EXTENT; ++ii)
        {
            stride *= comboIds[ii];
        }
        comboIds[i] = comboId / stride;
        comboId %= stride;
    }

    return { combos[comboIds[idxs]]... };
}
```

## End note

I believe the design outlined above is sufficient for parsing my configuration language using my versatile parser helpers. Leveraging this generic parser and tokenizer, I can effortlessly tokenize my JSON-like language. Furthermore, extending the semantics and grammar proved to be a straightforward task.

```cpp
// 190 lines of code is all needed to write the semantics, grammar and parse
namespace cbe_config
{

enum CfgTokensTypes : TokenType
{
    CFG_Comment,
    CFG_Assignment,
    CFG_CpyAssignment,
    CFG_Add,
    CFG_Remove,
    CFG_MultilineQuote,
    CFG_Quote,
    CFG_Escape,
    CFG_LineFeed,
    CFG_ScopeDeclStart,
    CFG_ScopeDeclEnd,
    CFG_ScopeSeparator,
    CFG_SectionStart,
    CFG_SectionEnd,
    /* Semantic tokens */
    CFG_CommentStr,
    CFG_VarAssignment,
    CFG_VarUse,
    CFG_VarIndex,
    CFG_StringValue,
    CFG_NumberValue
};
#define VAR_NAME_PATTERN "[a-zA-Z_]{1}[a-zA-Z0-9_]*"
static StringRegex LF_RE{ TCHAR("\r?\n"), std::regex_constants::ECMAScript };
static StringRegex VAR_NAME_RE{ TCHAR(COMBINE("^", VAR_NAME_PATTERN)), std::regex_constants::ECMAScript };
static StringRegex ANY_RE{ TCHAR(".*"), std::regex_constants::ECMAScript };
static StringRegex MULTILINE_STRING_VALUE{ TCHAR("(?:\"{3}|'{3})([\\s\\S]*?)(?:\"{3}|'{3})"), std::regex_constants::ECMAScript };
static StringRegex QUOTED_STRING_VALUE{ TCHAR("['\"](.+)['\"]"), std::regex_constants::ECMAScript };
static StringRegex ANY_NUMBER_VAL{ TCHAR("[-+]?\\d*[.]?\\d+"), std::regex_constants::ECMAScript };
/* Selects everything continuous breaks when encountering space or special characters listed */
static StringRegex ANY_STRING_VALUE{ TCHAR("([^\\s#]+)"), std::regex_constants::ECMAScript };
static StringRegex VAR_USE_RE{ TCHAR(COMBINE(COMBINE("/(", VAR_NAME_PATTERN), ")")), std::regex_constants::ECMAScript };
static StringRegex VAR_IDX_RE{ TCHAR("/(\\d+)"), std::regex_constants::ECMAScript };

static BasicTokenDesc BASIC_TOKENS[] = {
    {       CFG_Comment,               TokenizerPattern::make<ETokenPatternType::CharMatch>('#', 1, 1,  true, false)},
    {    CFG_Assignment,               TokenizerPattern::make<ETokenPatternType::CharMatch>('=', 1, 1, false, false)},
    { CFG_CpyAssignment,     TokenizerPattern::make<ETokenPatternType::StringMatch>(TCHAR(":="), 1, 1, false, false)},
    {           CFG_Add,               TokenizerPattern::make<ETokenPatternType::CharMatch>('+', 1, 1, false, false)},
    {        CFG_Remove,               TokenizerPattern::make<ETokenPatternType::CharMatch>('-', 1, 1, false, false)},
    {CFG_MultilineQuote,    TokenizerPattern::make<ETokenPatternType::StringMatch>(TCHAR("'''"), 1, 1, false,  true)},
    {CFG_MultilineQuote, TokenizerPattern::make<ETokenPatternType::StringMatch>(TCHAR("\"\"\""), 1, 1, false,  true)},
    {         CFG_Quote,              TokenizerPattern::make<ETokenPatternType::CharMatch>('\'', 1, 1, false,  true)},
    {         CFG_Quote,               TokenizerPattern::make<ETokenPatternType::CharMatch>('"', 1, 1, false,  true)},
    {      CFG_LineFeed,                TokenizerPattern::make<ETokenPatternType::Regex>(&LF_RE, 1, 1, false, false)},
    {CFG_ScopeDeclStart,               TokenizerPattern::make<ETokenPatternType::CharMatch>('[', 1, 1, false,  true)},
    {  CFG_ScopeDeclEnd,               TokenizerPattern::make<ETokenPatternType::CharMatch>(']', 1, 1, false,  true)},
    {CFG_ScopeSeparator,               TokenizerPattern::make<ETokenPatternType::CharMatch>('/', 1, 1,  true,  true)},
    {  CFG_SectionStart,               TokenizerPattern::make<ETokenPatternType::CharMatch>('{', 1, 1, false,  true)},
    {    CFG_SectionEnd,               TokenizerPattern::make<ETokenPatternType::CharMatch>('}', 1, 1, false,  true)},
};

namespace cmt_str
{
constexpr SemanticTokenDesc P1[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_Comment, 1, 1, true, true), 0, false},
};
constexpr SemanticTokenDesc P2[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&ANY_RE, 1, 1, false, false), CFG_CommentStr, true},
};
constexpr SemanticTokenDesc P3[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_LineFeed, 1, 1, false, false), 0, false},
    {             TokenizerPattern::make<ETokenPatternType::Eof>(0, 1, 1, false, false), 0, false},
};

} // namespace cmt_str

constexpr static const auto COMMENT_STR_WORDS_1 = ParseHelpers::createCombinations(cmt_str::P1, cmt_str::P2, cmt_str::P3);
#define CMT_STR_WORDS(FirstFn, Fn, LastFn) FirstFn(COMMENT_STR_WORDS_1)

namespace var_use_copy
{
constexpr SemanticTokenDesc P1[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_NAME_RE, 1, 1, false, true), CFG_VarAssignment, true},
};
constexpr SemanticTokenDesc P2[] = {
    {   TokenizerPattern::make<ETokenPatternType::Token>(CFG_Add, 1, 1, false, false), 0, false},
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_Remove, 1, 1, false, false), 0, false},
};
constexpr SemanticTokenDesc P3[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_CpyAssignment, 1, 1, false, true), 0, false},
};
constexpr SemanticTokenDesc P4[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_USE_RE, 1, 1, true, false), CFG_VarUse, true},
};
constexpr SemanticTokenDesc P5[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_IDX_RE, 1, 1, false, false), CFG_VarIndex, true},
};

} // namespace var_use_copy

/* Referencing an element in array variable with index */
constexpr static const auto VAR_USE_IN_ASSIGN_WORDS_1
    = ParseHelpers::createCombinations(var_use_copy::P1, var_use_copy::P2, var_use_copy::P3, var_use_copy::P4, var_use_copy::P5);
constexpr static const auto VAR_USE_IN_ASSIGN_WORDS_2
    = ParseHelpers::createCombinations(var_use_copy::P1, var_use_copy::P3, var_use_copy::P4, var_use_copy::P5);
/* Referencing variable directly */
constexpr static const auto VAR_USE_IN_ASSIGN_WORDS_3
    = ParseHelpers::createCombinations(var_use_copy::P1, var_use_copy::P2, var_use_copy::P3, var_use_copy::P4);
constexpr static const auto VAR_USE_IN_ASSIGN_WORDS_4 = ParseHelpers::createCombinations(var_use_copy::P1, var_use_copy::P3, var_use_copy::P4);
#define VAR_USE_COPY_WORDS(FirstFn, Fn, LastFn)                                                                                                \
    FirstFn(VAR_USE_IN_ASSIGN_WORDS_1) Fn(VAR_USE_IN_ASSIGN_WORDS_2) Fn(VAR_USE_IN_ASSIGN_WORDS_3) LastFn(VAR_USE_IN_ASSIGN_WORDS_4)

namespace var_use_in_scope
{
constexpr SemanticTokenDesc P1[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_ScopeDeclStart, 1, 1, false, true), 0, false},
};
constexpr SemanticTokenDesc P2[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_USE_RE, 1, 1, true, false), CFG_VarUse, true},
};
constexpr SemanticTokenDesc P3[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_IDX_RE, 1, 1, false, false), CFG_VarIndex, true},
};
constexpr SemanticTokenDesc P4[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_ScopeDeclEnd, 1, 1, false, false), 0, false},
};
} // namespace var_use_in_scope

constexpr static const auto VAR_USE_IN_SCOPE_DECL_WORDS_1
    = ParseHelpers::createCombinations(var_use_in_scope::P1, var_use_in_scope::P2, var_use_in_scope::P4);
/* Referencing an element in array variable with index */
constexpr static const auto VAR_USE_IDX_IN_SCOPE_DECL_WORDS_1
    = ParseHelpers::createCombinations(var_use_in_scope::P1, var_use_in_scope::P2, var_use_in_scope::P3, var_use_in_scope::P4);
#define VAR_USE_IN_SCOPE_DECL_WORDS(FirstFn, Fn, LastFn) FirstFn(VAR_USE_IN_SCOPE_DECL_WORDS_1) LastFn(VAR_USE_IDX_IN_SCOPE_DECL_WORDS_1)

/* Direct assignment to some value, copy from another var will not be parsed here */
namespace var_assign
{

constexpr SemanticTokenDesc P1[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_NAME_RE, 1, 1, false, true), CFG_VarAssignment, true},
};
constexpr SemanticTokenDesc P2[] = {
    {   TokenizerPattern::make<ETokenPatternType::Token>(CFG_Add, 1, 1, false, false), 0, false},
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_Remove, 1, 1, false, false), 0, false},
};
constexpr SemanticTokenDesc P3[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_Assignment, 1, 1, false, true), 0, false},
};
constexpr SemanticTokenDesc P4[] = {
    {       TokenizerPattern::make<ETokenPatternType::Token>(CFG_SectionStart, 1, 1, false, true),               0, false},
    {TokenizerPattern::make<ETokenPatternType::Regex>(&MULTILINE_STRING_VALUE, 1, 1, false, true), CFG_StringValue,  true},
    {   TokenizerPattern::make<ETokenPatternType::Regex>(&QUOTED_STRING_VALUE, 1, 1, false, true), CFG_StringValue,  true},
    {        TokenizerPattern::make<ETokenPatternType::Regex>(&ANY_NUMBER_VAL, 1, 1, false, true), CFG_NumberValue,  true},
    {      TokenizerPattern::make<ETokenPatternType::Regex>(&ANY_STRING_VALUE, 1, 1, false, true), CFG_StringValue,  true},
};

} // namespace var_assign

constexpr static const auto VAR_ASSIGN_WORDS_1
    = ParseHelpers::createCombinations(var_assign::P1, var_assign::P2, var_assign::P3, var_assign::P4);
constexpr static const auto VAR_ASSIGN_WORDS_2 = ParseHelpers::createCombinations(var_assign::P1, var_assign::P3, var_assign::P4);
#define VAR_ASSIGN_WORDS(FirstFn, Fn, LastFn) FirstFn(VAR_ASSIGN_WORDS_1) LastFn(VAR_ASSIGN_WORDS_2)

#define FOR_EACH_CBE_CONFIG_PATTERNS_UNIQUE_FIRST_LAST(FirstFn, Fn, LastFn)                                                                    \
    CMT_STR_WORDS(FirstFn, Fn, Fn) VAR_USE_IN_SCOPE_DECL_WORDS(Fn, Fn, Fn) VAR_USE_COPY_WORDS(Fn, Fn, Fn) VAR_ASSIGN_WORDS(Fn, Fn, LastFn)
#define FOR_EACH_CBE_CONFIG_PATTERNS(Fn) FOR_EACH_CBE_CONFIG_PATTERNS_UNIQUE_FIRST_LAST(Fn, Fn, Fn)

/* Update here whenever adding new semantic tokens */
#define CBE_CONFIG_PATTERNS_EXTENT_FIRST(Pat) ParseHelpers::COMBO_EXTENT<decltype(Pat)>
#define CBE_CONFIG_PATTERNS_EXTENT(Pat) +ParseHelpers::COMBO_EXTENT<decltype(Pat)>
constexpr SizeT TOTAL_SEMANTIC_TOKEN_SENETENCES
    = FOR_EACH_CBE_CONFIG_PATTERNS_UNIQUE_FIRST_LAST(CBE_CONFIG_PATTERNS_EXTENT_FIRST, CBE_CONFIG_PATTERNS_EXTENT, CBE_CONFIG_PATTERNS_EXTENT);
#undef CBE_CONFIG_PATTERNS_EXTENT
#undef CBE_CONFIG_PATTERNS_EXTENT_FIRST

#define CBE_CONFIG_COPY_PATTERNS_SEMANTICS(Pat)                                                                                                \
    for (SizeT i = 0; i < ParseHelpers::COMBO_EXTENT<decltype(Pat)>; ++i)                                                                      \
    {                                                                                                                                          \
        outSentences[currOffset++] = { .words = Pat[i] };                                                                                      \
    }
void makeSemanticSentences(ArrayRange<SemanticSentenceDesc> outSentences)
{
    debugAssertf(
        outSentences.size() >= TOTAL_SEMANTIC_TOKEN_SENETENCES, "Minimum {} SemanticeSentenceDesc is required!", TOTAL_SEMANTIC_TOKEN_SENETENCES
    );

    SizeT currOffset = 0;
    FOR_EACH_CBE_CONFIG_PATTERNS(CBE_CONFIG_COPY_PATTERNS_SEMANTICS)

    debugAssertf(
        currOffset == TOTAL_SEMANTIC_TOKEN_SENETENCES, "Tokens count({}) mismatch with sentence semantics written out({})!",
        TOTAL_SEMANTIC_TOKEN_SENETENCES, currOffset
    );
}
#undef CBE_CONFIG_COPY_PATTERNS_SEMANTICS

} // namespace cbe_config

void testCodesStart()
{
    String folder = PathFunctions::combinePath(TCHAR(".."), TCHAR(".."), TCHAR("Source/Runtime/ExampleModules/DummyApp/Shaders"));
    folder = PathFunctions::toAbsolutePath(folder, Paths::engineRoot());
    testShaderCompiler(folder);

    ParseHelpers::checkCreateCombinations();

    StopWatch sw;
    String configText;
    FileHelper::readString(configText, PathFunctions::combinePath(folder, TCHAR("SimpleConfig.txt")));
    LOG("DummyApp", "Sample file read in {}ms", StopWatch::WatchTime::asMilliSeconds(sw.currentLapTick()));
    sw.lap();

    ParseHelpers::ArenaAlloc allocator{ 16 * 1024 };
    ArrayRange basicTokens = ParseHelpers::parseBasicTokens(cbe_config::BASIC_TOKENS, configText, allocator);
    LOG("DummyApp", "Basic tokens parsed in {}ms", StopWatch::WatchTime::asMilliSeconds(sw.currentLapTick()));
    sw.lap();

    std::array<SemanticSentenceDesc, cbe_config::TOTAL_SEMANTIC_TOKEN_SENETENCES> semanticDescs;
    cbe_config::makeSemanticSentences(semanticDescs);
    LOG("DummyApp", "Semantics copied in {}ms", StopWatch::WatchTime::asMilliSeconds(sw.currentLapTick()));
    sw.lap();

    ArrayRange tokens = ParseHelpers::parseSemanticTokens(semanticDescs, basicTokens, configText, allocator);
    LOG("DummyApp", "Semantic tokens parsed in {}ms", StopWatch::WatchTime::asMilliSeconds(sw.currentLapTick()));
    sw.stop();
}
```

[//]: # (Below are link reference definitions)
