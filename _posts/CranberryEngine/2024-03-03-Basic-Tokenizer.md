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
Additional tokens like variable names, text concat across lines can be obtained from second semantic token pass.

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
Third pass is scoping pass where all the scopes are validated.

In our case there are only three scopes

- Scope decl `[...]`
- Scope section `{...}`
- Text `"..."` `'...'`

This pass must receive the entire list of scope tokens, validates the scopes.

{: .emphasis}
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

This pass requires the previously created list of `ParsedTokens` as input and output. Input is list of grammar as list of `SemanticSentance`. Both subexpressions and token patterns are supported in addition to other pattern types.

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

Receives list of scope tokens and validates if the scopes are complete. Input must be list of `ParsedTokens` and list of `ScopeTokens`. The errors are returned in list of `ParseError`.

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

Receives list of scope tokens similar to pass 3 and groups the subtokens into it. Input must be list of `ParsedTokens` and list of `ScopeTokens`. The errors are returned in list of `ParseError`. Also returns list of `TokensGroup` which contains the `ParsedTokens` range which are inside a scope.
This functionality could be combined with Pass 3 to group conditionally.

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

Checks the grammatical correctness and returns the errors if any as list of `ParseError`. Input is list of `SentenceGrammar`, `ParsedTokens` and `TokensGroup`. Also returns list of `GrammarMatchesPerGroup` for each `SentenceGrammar` inside each group.

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

While contemplating all conceivable combinations of sentence semantics, I swiftly recognized the necessity for an improved approach. Consequently, I devised the following helper functions to handle these combinations. Notably, the code generation occurs during compile time, while the data population takes place at program startup.

```cpp
template <typename T, SizeT Extent, SizeT Rank, typename... TCombos>
constexpr static void createCombinations(T (&arr)[Extent][Rank], TCombos &&...combos)
{
    static_assert(Rank == sizeof...(combos), "Rank mismatch when creating combination");
    static_assert(std::conjunction_v<std::is_array<std::remove_cvref_t<TCombos>>...>, "All combinations must be an array");
    static_assert(
        std::conjunction_v<std::is_same<std::remove_all_extents_t<std::remove_cvref_t<TCombos>>, T>...>,
        "All combinations must be of same type as out array"
    );

    for (SizeT i = 0; i < Extent; ++i)
    {
        createCombos(std::index_sequence_for<TCombos...>{}, arr[i], i, std::forward<TCombos>(combos)...);
    }
}

template <SizeT idx, SizeT... idxs, typename T, SizeT Rank, SizeT N, typename... TCombos>
constexpr static void
createCombos(std::index_sequence<idx, idxs...>, T (&arr)[Rank], SizeT comboIdx, const T (&combo)[N], TCombos &&...combos)
{
    static_assert(sizeof...(combos) == sizeof...(idxs), "Something is VERY wrong!");

    if constexpr (sizeof...(combos) != 0)
    {
        constexpr static const SizeT STRIDE = COMBO_EXTENT<std::remove_cvref_t<TCombos>...>;
        createCombos(std::index_sequence<idxs...>{}, arr, comboIdx % STRIDE, std::forward<TCombos>(combos)...);
        arr[idx] = combo[comboIdx / STRIDE];
    }
    else
    {
        arr[idx] = combo[comboIdx];
    }
}
```

## End note

I believe the design outlined above is sufficient for parsing my configuration language using my versatile parser helpers. Leveraging this generic parser and tokenizer, I can effortlessly tokenize my JSON-like language. Furthermore, extending the semantics and grammar proved to be a straightforward task. 🚀

```cpp
// 180 lines of code is all needed to write the semantics, grammar and parse

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
static SemanticTokenDesc P1[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_Comment, 1, 1, true, true), 0, false},
};
static SemanticTokenDesc P2[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&ANY_RE, 1, 1, false, false), CFG_CommentStr, true},
};
static SemanticTokenDesc P3[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_LineFeed, 1, 1, false, false), 0, false},
    {             TokenizerPattern::make<ETokenPatternType::Eof>(0, 1, 1, false, false), 0, false},
};

constexpr static const SizeT C1_EXTENT = ParseHelpers::COMBO_EXTENT<decltype(P1), decltype(P2), decltype(P3)>;
constexpr static const SizeT C1_RANK = ParseHelpers::COMBO_RANK<decltype(P1), decltype(P2), decltype(P3)>;

} // namespace cmt_str

static SemanticTokenDesc COMMENT_STR_WORDS_1[cmt_str::C1_EXTENT][cmt_str::C1_RANK];
DO_ONCE_GLOBAL(ParseHelpers::createCombinations(COMMENT_STR_WORDS_1, cmt_str::P1, cmt_str::P2, cmt_str::P3));
#define CMT_STR_EXTENT cmt_str::C1_EXTENT

namespace var_use
{
static SemanticTokenDesc P1[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_NAME_RE, 1, 1, false, true), CFG_VarAssignment, true},
};
static SemanticTokenDesc P2[] = {
    {   TokenizerPattern::make<ETokenPatternType::Token>(CFG_Add, 1, 1, false, false), 0, false},
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_Remove, 1, 1, false, false), 0, false},
};
static SemanticTokenDesc P3[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_CpyAssignment, 1, 1, false, true), 0, false},
};
static SemanticTokenDesc P4[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_USE_RE, 1, 1, true, false), CFG_VarUse, true},
};
static SemanticTokenDesc P5[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_IDX_RE, 1, 1, false, false), CFG_VarIndex, true},
};

/* Referencing an element in array variable with index */
constexpr static const SizeT C1_EXTENT = ParseHelpers::COMBO_EXTENT<decltype(P1), decltype(P2), decltype(P3), decltype(P4), decltype(P5)>;
constexpr static const SizeT C1_RANK = ParseHelpers::COMBO_RANK<decltype(P1), decltype(P2), decltype(P3), decltype(P4), decltype(P5)>;
constexpr static const SizeT C2_EXTENT = ParseHelpers::COMBO_EXTENT<decltype(P1), decltype(P3), decltype(P4), decltype(P5)>;
constexpr static const SizeT C2_RANK = ParseHelpers::COMBO_RANK<decltype(P1), decltype(P3), decltype(P4), decltype(P5)>;

/* Referencing variable directly */
constexpr static const SizeT C3_EXTENT = ParseHelpers::COMBO_EXTENT<decltype(P1), decltype(P2), decltype(P3), decltype(P4)>;
constexpr static const SizeT C3_RANK = ParseHelpers::COMBO_RANK<decltype(P1), decltype(P2), decltype(P3), decltype(P4)>;
constexpr static const SizeT C4_EXTENT = ParseHelpers::COMBO_EXTENT<decltype(P1), decltype(P3), decltype(P4)>;
constexpr static const SizeT C4_RANK = ParseHelpers::COMBO_RANK<decltype(P1), decltype(P3), decltype(P4)>;

} // namespace var_use

static SemanticTokenDesc VAR_USE_IN_ASSIGN_WORDS_1[var_use::C1_EXTENT][var_use::C1_RANK];
static SemanticTokenDesc VAR_USE_IN_ASSIGN_WORDS_2[var_use::C2_EXTENT][var_use::C2_RANK];
static SemanticTokenDesc VAR_USE_IN_ASSIGN_WORDS_3[var_use::C3_EXTENT][var_use::C3_RANK];
static SemanticTokenDesc VAR_USE_IN_ASSIGN_WORDS_4[var_use::C4_EXTENT][var_use::C4_RANK];

DO_ONCE_GLOBAL(ParseHelpers::createCombinations(VAR_USE_IN_ASSIGN_WORDS_1, var_use::P1, var_use::P2, var_use::P3, var_use::P4, var_use::P5));
DO_ONCE_GLOBAL(ParseHelpers::createCombinations(VAR_USE_IN_ASSIGN_WORDS_2, var_use::P1, var_use::P3, var_use::P4, var_use::P5));
DO_ONCE_GLOBAL(ParseHelpers::createCombinations(VAR_USE_IN_ASSIGN_WORDS_3, var_use::P1, var_use::P2, var_use::P3, var_use::P4));
DO_ONCE_GLOBAL(ParseHelpers::createCombinations(VAR_USE_IN_ASSIGN_WORDS_4, var_use::P1, var_use::P3, var_use::P4));
#define VAR_USE_EXTENT CMT_STR_EXTENT + var_use::C1_EXTENT + var_use::C2_EXTENT + var_use::C3_EXTENT + var_use::C4_EXTENT

static SemanticTokenDesc VAR_USE_IN_SCOPE_DECL_WORDS[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_ScopeDeclStart, 1, 1, false,  true),          0, false},
    {       TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_USE_RE, 1, 1,  true, false), CFG_VarUse,  true},
    {  TokenizerPattern::make<ETokenPatternType::Token>(CFG_ScopeDeclEnd, 1, 1, false, false),          0, false},
};
/* Referencing an element in array variable with index */
static SemanticTokenDesc VAR_USE_IDX_IN_SCOPE_DECL_WORDS[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_ScopeDeclStart, 1, 1, false,  true),            0, false},
    {       TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_USE_RE, 1, 1,  true, false),   CFG_VarUse,  true},
    {       TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_IDX_RE, 1, 1, false, false), CFG_VarIndex,  true},
    {  TokenizerPattern::make<ETokenPatternType::Token>(CFG_ScopeDeclEnd, 1, 1, false, false),            0, false},
};
#define VAR_USE_IN_SCOPE_DECL_EXTENT VAR_USE_EXTENT + 2

/* Direct assignment to some value, copy from another var will not be parsed here */
namespace var_assign
{

static SemanticTokenDesc P1[] = {
    {TokenizerPattern::make<ETokenPatternType::Regex>(&VAR_NAME_RE, 1, 1, false, true), CFG_VarAssignment, true},
};
static SemanticTokenDesc P2[] = {
    {   TokenizerPattern::make<ETokenPatternType::Token>(CFG_Add, 1, 1, false, false), 0, false},
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_Remove, 1, 1, false, false), 0, false},
};
static SemanticTokenDesc P3[] = {
    {TokenizerPattern::make<ETokenPatternType::Token>(CFG_Assignment, 1, 1, false, true), 0, false},
};
static SemanticTokenDesc P4[] = {
    {       TokenizerPattern::make<ETokenPatternType::Token>(CFG_SectionStart, 1, 1, false, true),               0, false},
    {TokenizerPattern::make<ETokenPatternType::Regex>(&MULTILINE_STRING_VALUE, 1, 1, false, true), CFG_StringValue,  true},
    {   TokenizerPattern::make<ETokenPatternType::Regex>(&QUOTED_STRING_VALUE, 1, 1, false, true), CFG_StringValue,  true},
    {        TokenizerPattern::make<ETokenPatternType::Regex>(&ANY_NUMBER_VAL, 1, 1, false, true), CFG_NumberValue,  true},
    {      TokenizerPattern::make<ETokenPatternType::Regex>(&ANY_STRING_VALUE, 1, 1, false, true), CFG_StringValue,  true},
};

constexpr static const SizeT C1_EXTENT = ParseHelpers::COMBO_EXTENT<decltype(P1), decltype(P2), decltype(P3), decltype(P4)>;
constexpr static const SizeT C1_RANK = ParseHelpers::COMBO_RANK<decltype(P1), decltype(P2), decltype(P3), decltype(P4)>;

constexpr static const SizeT C2_EXTENT = ParseHelpers::COMBO_EXTENT<decltype(P1), decltype(P3), decltype(P4)>;
constexpr static const SizeT C2_RANK = ParseHelpers::COMBO_RANK<decltype(P1), decltype(P3), decltype(P4)>;

} // namespace var_assign

static SemanticTokenDesc VAR_ASSIGN_WORDS_1[var_assign::C1_EXTENT][var_assign::C1_RANK];
static SemanticTokenDesc VAR_ASSIGN_WORDS_2[var_assign::C2_EXTENT][var_assign::C2_RANK];

DO_ONCE_GLOBAL(ParseHelpers::createCombinations(VAR_ASSIGN_WORDS_1, var_assign::P1, var_assign::P2, var_assign::P3, var_assign::P4));
DO_ONCE_GLOBAL(ParseHelpers::createCombinations(VAR_ASSIGN_WORDS_2, var_assign::P1, var_assign::P3, var_assign::P4));
#define VAR_ASSIGN_EXTENT VAR_USE_IN_SCOPE_DECL_EXTENT + var_assign::C1_EXTENT + var_assign::C2_EXTENT

/* Update here whenever adding new semantic tokens */
constexpr static const SizeT TOTAL_SEMANTIC_TOKEN_SENETENCES = VAR_ASSIGN_EXTENT;
#undef VAR_ASSIGN_EXTENT
#undef VAR_USE_IN_SCOPE_DECL_EXTENT
#undef VAR_USE_EXTENT
#undef CMT_STR_EXTENT

void makeSemanticSentences(ArrayRange<SemanticSentenceDesc> outSentences)
{
    debugAssertf(
        outSentences.size() >= TOTAL_SEMANTIC_TOKEN_SENETENCES, "Minimum {} SemanticeSentenceDesc is required!", TOTAL_SEMANTIC_TOKEN_SENETENCES
    );

    SizeT currOffset = 0;
    /* comment strings */
    for (SizeT i = 0; i < cmt_str::C1_EXTENT; ++i)
    {
        outSentences[currOffset++] = { .words = COMMENT_STR_WORDS_1[i] };
    }
    /* basic tokens */
    outSentences[currOffset++] = { .words = VAR_USE_IDX_IN_SCOPE_DECL_WORDS };
    outSentences[currOffset++] = { .words = VAR_USE_IN_SCOPE_DECL_WORDS };

    /* variable use in scope declaration or copy assignment */
    for (SizeT i = 0; i < var_use::C1_EXTENT; ++i)
    {
        outSentences[currOffset++] = { .words = VAR_USE_IN_ASSIGN_WORDS_1[i] };
    }
    for (SizeT i = 0; i < var_use::C2_EXTENT; ++i)
    {
        outSentences[currOffset++] = { .words = VAR_USE_IN_ASSIGN_WORDS_2[i] };
    }
    for (SizeT i = 0; i < var_use::C3_EXTENT; ++i)
    {
        outSentences[currOffset++] = { .words = VAR_USE_IN_ASSIGN_WORDS_3[i] };
    }
    for (SizeT i = 0; i < var_use::C4_EXTENT; ++i)
    {
        outSentences[currOffset++] = { .words = VAR_USE_IN_ASSIGN_WORDS_4[i] };
    }

    /* variable assignment */
    for (SizeT i = 0; i < var_assign::C1_EXTENT; ++i)
    {
        outSentences[currOffset++] = { .words = VAR_ASSIGN_WORDS_1[i] };
    }
    for (SizeT i = 0; i < var_assign::C2_EXTENT; ++i)
    {
        outSentences[currOffset++] = { .words = VAR_ASSIGN_WORDS_2[i] };
    }

    debugAssertf(
        currOffset == TOTAL_SEMANTIC_TOKEN_SENETENCES, "Tokens count({}) mismatch with sentence semantics written out({})!",
        TOTAL_SEMANTIC_TOKEN_SENETENCES, currOffset
    );
}

} // namespace cbe_config

void testCodesStart()
{
    String folder = PathFunctions::combinePath(TCHAR(".."), TCHAR(".."), TCHAR("Source/Runtime/ExampleModules/DummyApp/Shaders"));
    folder = PathFunctions::toAbsolutePath(folder, Paths::engineRoot());
    testShaderCompiler(folder);

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
