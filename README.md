# texp

texp is a plain TeX tokeniser and macro expander, but not a type-setter. In Knuth's terminology, texp implements the eyes, mouth and some parts of stomach that are not concerned with typesetting.

The way texp works is that it reads input, tokenises it, macro expands the tokens, then executes tokens that are left and understood by texp, and what is left is send to stdout.


## Supported macros and commands

* `\input`, `\endinput`
* `\def`
* `\let`
* `\csname`
* `\epxandafter`
* `\ifx`, `\iftrue`, `\iffalse`
* `\relax`
* `\catcode`
* active characters, e.g. ```\catcode`\~=13  \def~{Foo} ~Bar``` expands to `FooBar`.
* `\input`
* `\char`


## Example

Suppose the following is in a file `page.tex`.

```
\def\begintag#1{<#1>}%
\def\endtag#1{</#1>}%
\def\tag#1#2{\begintag{#1}#2\endtag{#1}}%
\def\par{\begintag{p}}%
%
\begintag{html}
    \tag{h1}{Title}

    Content

    Lorem ispum
\endtag{html}

```

When `./texp page.tex` is run. it procudes the following output:

```
<html> <h1>Title</h1> <p>Content <p>Lorem ispum </html>
```
