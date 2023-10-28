---
layout: single
title:  "Unicode and C++"
date:   2022-02-11
mathjax: true
categories: 
    - cranberry
header:
    teaser: /assets/images/CranberryEngine/Unicode/unicodes.png
---
## Unicode in my engine

Recently I converted my engine strings to use Unicode platform dependent encoding rather than previously used `ASCII` strings stored in Multi byte char array. This blog will be my understanding on what Unicode is and how they are encoded in UTF-8, UTF-16 or UTF-32.
If you do not know/understand what Unicode and It's encoding means read [The absolute minimum every Software Developer]

### Brief on Unicode

What is **`Unicode`**{: style="color: red;" }?
In a very simple terms, It is just a table with every characters from some popularly spoken language around the world mapped to a code word(`Unicode`).
This code word is also called as **`Code Point`**{: style="color: red;" }.

> #### **It All Started Here**
>
> If in childhood you have ever created some simple encryption to write your personal diary to avoid your friend/sister from reading it? I did and it was just a bunch of roman numerals mapped to each charater in english alphabets. Example A -> IX and so on for each character. Ofcourse I cannot remember all of those `Code Points` so I wrote them in a paper(I lost it however 😔(Even this emoji is just an Unicode code point)).
This is exactly what Unicode does but with large number of characters from most languages in the world, with math notations, emoji, etc.,
I hope this clears what Unicode is and what code point means.

At this point it seems that there is no need for any additional representations to represent any characters. If you are feeling same then you are right. However computer word sizes are not unlimited so, In order to represent this unicode within the limits of computer units encodings were developed, Some of the popular ones are `UTF-8, UTF-16, UTF-32`.

> Before saying what these encodings mean generally. I would like to tell another story which is a problem I encountered when I created this [encoding](#it-all-started-here). When I created it I wanted to not only write one letter words, I want ability to write entire words with multiple letters. If I represented everything in roman numerals how will I be able decode it? example If I write something like `XIVXV` in this how do I aggregate a set of roman numerals as one english letter. I realised that the problem to decode comes from limitation in number of distinct looking roman numerals. So I did following to remedy that
>
>* I split english letters into three set of characters each containing <= 10 letters
>* Each alphabet is represented as 2 to 4 roman numerals
>* First set of english alphabets are prefixed with `L` so `*A* is **LI**, *B* is **LII** ... *J* is **LX**
>* Second set of english alphabets are prefixed with `C` so `*K* is **CI**, *L* is **CII** ... *T* is **CX**
>* Third set of english alphabets are prefixed with `M` so `*U* is **MI**, *V* is **MII** ... *Z* is **MVI**
>* Obviously this is inefficient. A 3 letter word requires minimum 6 letters and maximum 12Letters but my tiny brain cannot think beyond that at that point.

You see this is exactly what Unicode encoding does. These sections are called as **`Code pages`**{: style="color: red;" } in unicode. `Code pages` allows us to use the same code point but with different representations.

So far we have seen `Code points` and `Code pages`. Code points are entries in a table mapping characters to code and Code pages are distinct tables.

### Encodings

Please note that in below encoding descriptions I made assumptions that we are only supporting codepoints that can be represented using 4Bytes. For all characters or emoji using 2 or more codepoints please refer [Emoji sets]

#### UTF-8

UTF-8 is the best of three popular unicode encoding in my opinion and also because most of the `Basic Multilingual Plane(BMP)` fits within 2Bytes width. It is also endianess safe to use. UTF-8 can occupy from 1Byte to 4Bytes(Although there are cases it will be more, Those case are not mandatory to handle). In the table below you can see that UTF-8 encodes first 128 codepoints in 1 byte, upto first 2048 codepoints in 2 bytes, and rest of BMP in 3 bytes.

Code point <-> UTF-8 conversion([UTF-8 to codepoints])

| First code point  | Last code point   | Byte 1    | Byte 2    | Byte 3    | Byte 4    |
| ----------------- | ----------------- | --------- | --------- | --------- | --------- |
| U+0000            | U+007F            | 0xxxxxxx  |           |           |           |
| U+0080            | U+07FF            | 110xxxxx  | 10xxxxxx  |           |           |
| U+0800            | U+FFFF            | 1110xxxx  | 10xxxxxx  | 10xxxxxx  |           |
| U+10000           | U+10FFFF          | 11110xxx  | 10xxxxxx  | 10xxxxxx  | 10xxxxxx  |

More over, For just display character cases as UTF-8 encodes first 128 codes in 1Byte, Most of the application internal strings can be encoded in 1Byte and only `localization text` needs to be longer.

**Note** that if you are allowing any operation that needs to be done in `locale aware` manner then you have to decode first before performing any operation. One example will be sorting string based on displayed locale, Here you have to consider the language's rules when sorting.

#### UTF-16

The UTF-16 standard supports encoding the entire BMP in a word. So code points from `0 to 65535(0xFFFF)` can be encoded in a word. In order to accomplish that without collision from other planes Unicode standard reserved a range of codepoints`[0xD800, 0xDFFF]` for special purpose and never uses it for any character. This allows using this range as surrogates for higher and lower word in UTF-16.

Each plane is comprised of $2^{16}$`(0x10000)`. Unicode has total `17 such planes(1 BMP + 16 Supplementary planes`. To represent any code points above $2^{16}-1$`(0xFFFF)` UTF-16 uses 2 words(4Bytes). Even though it stores in 4Bytes it uses only 20bits for actual data. The reasoning behind that is we do `codepoint - 0x10000` when encoding a codepoint this is necessary in order to represent all supplementary plane in another `4bits(0-15 Supplementary planes)` with each plane having $2^{16}$`(16bits)` character codes. Now we have to split the subtracted codepoint into two 10bits value as High surrogate(11th bit to 20th bit) and Low surrogate(1st bit to 10th bit). The higher surrogate is added with `0xD800` and placed in lower index of word string, The lower surrogate is added with `0xDC00` and placed in higher index of word string. This gives us UTF-16 encoded multi-word character.

Read more at [UTF-16 Wiki]

```
U' = yyyyyyyyyyxxxxxxxxxx;  // U - 0x10000
W1 = 110110yyyyyyyyyy;      // 0xD800 + yyyyyyyyyy
W2 = 110111xxxxxxxxxx;      // 0xDC00 + xxxxxxxxxx
Str[2] = { W1, W2 };
```

#### UTF-32

UTF-32 always stores the entire codepoint directly in 4Bytes. So no matter if your characters are going to be only ASCII or some ancient language. it will always be 4Bytes.

## Engine

In my engine I chose to use UTF-8 as english and tamil characters can be contained in 1 or 2 Bytes. Also It is easier to compare strings with UTF-8 and UTF-32.

I have developed the code in engine such that I can switch to use platform specific wide-char with a macro and typedef flip.
In order to convert between UTF-8 and other encoding I am using platform functions where possible and use `std::codecvt` of stl library

>* While implementing this particular unicode converter tool came in handy - [Unicode Converter]
>* Conversion logics are explained well here [Unicode Desc]

Code to convert to UTF-8 from UTF-16/UTF-32

```cpp
template <typename BufferType, typename NonUtf8Type>
bool convertToUtf8(BufferType& buffer, const NonUtf8Type* start)
{
    auto& toUtf8 = std::use_facet<std::codecvt<NonUtf8Type, Utf8, std::mbstate_t>>(std::locale());
    const auto* end = String::recurseToNullEnd(start);

    // Convert from UTF-16/UTF-32 to UTF-8
    std::mbstate_t state{};
    const NonUtf8Type* nextFrom = nullptr;
    Utf8* nextTo = nullptr;

    buffer.resize(toUtf8.max_length() * (end - start), TCHAR('\0'));
    Utf8* outData = reinterpret_cast<Utf8*>(buffer.data());

    std::codecvt_base::result status = toUtf8.out(state
        , reinterpret_cast<const NonUtf8Type*>(start), reinterpret_cast<const NonUtf8Type*>(end), nextFrom
        , outData, outData + buffer.size(), nextTo);
    buffer.resize(nextTo - outData);
    if (status != std::codecvt_base::ok)
    {
        LOG_ERROR("StringConv", "Failed to convert to AChar(UTF-8)");
        buffer.clear();
        return false;
    }
    return true;
}
```

Code to convert to UTF-8 to UTF-16/UTF-32

```cpp
template <typename BufferType, typename NonUtf8Type = BufferType::value_type>
bool convertFromUtf8(BufferType& buffer, const AChar* start)
{
    auto& fromUtf8 = std::use_facet<std::codecvt<NonUtf8Type, Utf8, std::mbstate_t>>(std::locale());
    const auto* end = String::recurseToNullEnd(start);

    // Convert from UTF-8 to UTF-16/UTF-32
    std::mbstate_t state{};
    const Utf8* nextFrom = nullptr;
    NonUtf8Type* nextTo = nullptr;

    buffer.resize(end - start, TCHAR('\0'));
    NonUtf8Type* outData = reinterpret_cast<NonUtf8Type*>(buffer.data());
    std::codecvt_base::result status = fromUtf8.in(state
        , reinterpret_cast<const Utf8*>(start), reinterpret_cast<const Utf8*>(end), nextFrom
        , outData, outData + buffer.size(), nextTo);
    buffer.resize(nextTo - outData);
    if (status != std::codecvt_base::ok)
    {
        LOG_ERROR("StringConv", "Failed to convert from AChar(UTF-8)");
        buffer.clear();
        return false;
    }
    return true;
}
```

In order to convert encoded type(UTF-8 or UTF-16) to its code point. I have implemented two functions as below

```cpp
uint32 StringCodePointsHelper::utf8ToCode(const Utf8* firstChar, uint32 byteCount)
{
    uint32 codePoint = 0;
    switch (byteCount)
    {
    case 1:
        codePoint = (uint32)(*firstChar);
        break;
    case 2:
        codePoint = (*firstChar - 192u) * 64u
            + (*(firstChar + 1) - 128u);
        break;
    case 3:
        codePoint = (*firstChar - 224u) * 4096u
            + (*(firstChar + 1) - 128u) * 64u
            + (*(firstChar + 2) - 128u);
        break;
    case 4:
    default:
        // Handling anything above 4 bytes as 4 bytes and skip rest of the bytes
        codePoint = (*firstChar - 240u) * 262144u
            + (*(firstChar + 1) - 128u) * 4096u
            + (*(firstChar + 2) - 128u) * 64u
            + (*(firstChar + 3) - 128u);
        break;
    }
    return codePoint;
}

uint32 StringCodePointsHelper::utf16ToCode(const Utf16* firstChar)
{
    // Single wide char
    if ((*firstChar < 0xD800u) && (*firstChar >= 0xE000u))
    {
        return (uint32)(*firstChar);
    }
    return 0x10000u 
        + (*firstChar - 0xD800u) * 0x400u
        + (*(firstChar + 1) - 0xDC00u);
}
```

The above encoding to codepoints prints following output for input `zß水அ🍌✈😔`

```
[TEST][LOG]0x7a
[TEST][LOG]0xdf
[TEST][LOG]0x6c34
[TEST][LOG]0xb85
[TEST][LOG]0x1f34c
[TEST][LOG]0x2708
[TEST][LOG]0x1f614
```

Next step is rendering this codepoints as text.

***`Jeslas Pravin`***{: style="color: green;" }

[//]: # (Below are link reference definitions)
[The absolute minimum every Software Developer]: https://www.joelonsoftware.com/2003/10/08/the-absolute-minimum-every-software-developer-absolutely-positively-must-know-about-unicode-and-character-sets-no-excuses/
[UTF-8 to codepoints]: https://en.wikipedia.org/wiki/UTF-8#Encoding
[UTF-16 Wiki]: https://en.wikipedia.org/wiki/UTF-16#Description
[Emoji sets]: https://www.unicode.org/reports/tr51/tr51-18.html#Emoji_Sets
[Unicode Converter]: https://www.branah.com/unicode-converter
[Unicode Desc]: https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&item_id=IWS-AppendixA
