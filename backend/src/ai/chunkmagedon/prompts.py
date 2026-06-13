PATTERN_FINDER_AGENT_PROMPT = """
Extract the high quality regex patterns for hierarchical divisions of the provided document.
The divisions that can apear in the provided text are provided in the table below.

depth	Depth name	Common Names in Different Domains	Typical Numbering / ID Method
1	Volume	Volume, Tome, Book (when a work is split)	"Volume I", "Vol. A"
2	Part	Part, Unit, Division, Book (in multi-book volumes), Act (drama)	"Part 1", "Part A"
3	Chapter	Chapter, Module, Lesson (educational), Clause (in some standards)	"Chapter 1", "1."
4	Section	Section, Major Section, Heading-1	"1.1", "§1", "Section 1"
5	Subsection	Subsection, Sub-section, Heading-2, Clause (sometimes)	"1.1.1", "1.1(a)"
6	Sub-subsection	Sub-subsection, Heading-3, Subclause (standards), Article (treaties)	"1.1.1.1", "1.1.1.1.1"
7	Paragraph	Paragraph, para, ¶, Level-4 heading, Clause (legal)	"(1)", "(a)", "[1.1.1.1.1]"
8	Subparagraph	Subparagraph, Sub-para, Item (legal), Subclause (when nested deeply)	"(A)", "(i)", "(I)"
9	Clause / Item	Clause, Item, Indent, List element, bullet point (in unstructured text)	"(aa)", "●", "a."

The extracted patterns should be in the form of dictionary where each division pattern is an object with the following structure:
[
    {
        "depth": <number>, // The hierarchical level (1-9)
        "depth_name": <string>, // The name of the depth level (e.g., "Volume", "Part", "Chapter", etc.)
        "regex_pattern": <string> // The regex pattern prepared to extract the division preapared for the provided text. It should be a regex working for the entire document.
    }
]

The example output:
[
    {
        "depth": 4,
        "depth_name": "Section",
        "regex_pattern": <regex pattern here>
    },
    {
        "depth": 5,
        "depth_name": "Subsection",
        "regex pattern": <regex pattern here>
    }
]

If a certain level is not present in the provided text, omit. Prepare only patterns for the levels that are present in the provided text.
Here is the text to analyze:

"""