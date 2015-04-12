texp
====

texp is a library for parsing TeX like documents.

texp is meant to be an utility for writing custom document formats based on TeX
easy.

texp is not meant to be a replacement for TeX or any of its formats (macro
packages) like LaTeX. However, it should be powerful enough to implement those
if one desires to do so. The motivation for texp is that TeX tokeniser and
macro expander works really well for writing structured documents.  It is quite
frequent that one wants to introduce abbreviations for commonly occuring
patterns in a text and macros are perfect for this purpose.  This is what is
missing from most of structured text formats like Markdown, RST, etc.

texp implements the TeX tokeniser and macro expander.  The tokeniser faithfully
reimplements the TeX tokeniser and expander as specified in TeXBook and it
seems to accept the same in put as the TeX system.  texp is missing almost all
of the builtin macros found in TeX, but it should not be too difficult to
reimplement them. There some indiscrepencies by design with TeX, for example,
the way \def is implemented is equivalent to \long\def in TeX.

texp is not a typesetter! There is no intention of introducing layout
engine in texp. texp is also not intended to comply fully with TeX.

With extensions texp could be used as a preprocessor for TeX documents
themselves.

Example
=======

Here's a snippet to give an idea of texp API:

    >>> import texp
    >>> doc = texp.iter_pos('\def\macro#1{Macro #1}  Example \macro{1}')
    >>> tokens = texp.tokenize(doc)
    >>> expanded = texp.expand(tokens)
    >>> print(texp.tokenstream_to_str(expanded))
     Example Macro 1

