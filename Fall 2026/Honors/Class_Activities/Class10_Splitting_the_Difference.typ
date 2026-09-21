#set document(
  title: "Honors Class 10 Activity: Splitting the Difference",
  author: "Elements of Data Science",
  keywords: ("data science", "honors", "probability", "expected value", "distribution", "activity"),
)

#set page(
  paper: "us-letter",
  margin: (x: 1in, y: 1in),
)

#set par(justify: true, leading: 0.65em)
#set heading(numbering: none)
#set text(font: "Liberation Serif", size: 11pt, lang: "en", region: "us")

#show raw.where(block: true): it => block(
  fill: rgb("#f2f2f2"),
  inset: 8pt,
  radius: 3pt,
  width: 100%,
  text(font: "Liberation Mono", size: 9.5pt, it),
)
#show raw.where(block: false): it => text(font: "Liberation Mono", size: 9.5pt, it)

#show heading.where(level: 1): it => [
  #set align(center)
  #set text(size: 15pt, weight: "bold")
  #block(above: 0pt, below: 12pt, it.body)
]
#show heading.where(level: 2): it => [
  #set text(size: 12pt, weight: "bold")
  #block(above: 14pt, below: 6pt, it.body)
]

#let question(body) = block(
  width: 100%,
  inset: (left: 8pt, top: 4pt, bottom: 4pt),
  stroke: (left: 2pt + rgb("#4a4a4a")),
  text(weight: "bold", body),
)

#let blank(width: 2.5cm) = box(
  width: width,
  height: 0.9em,
  stroke: (bottom: 0.5pt + black),
)

#let answer-space(height: 2cm) = block(height: height, width: 100%)

= Splitting the Difference

#set par(justify: false)
*Team Members:* #blank(width: 3.4cm) #h(0.2cm) #blank(width: 3.4cm) #h(0.2cm) #blank(width: 3.4cm)

#v(0.2cm)
#h(2.55cm) #blank(width: 3.4cm) #h(0.2cm) #blank(width: 3.4cm)
#set par(justify: true)

#v(0.2cm)

Your aunt and uncle are getting divorced. Rather than argue over who gets what, they have
agreed to settle it with a coin. For each item on the household inventory they will flip
once: heads to your aunt, tails to your uncle. Nobody chooses, nobody negotiates, nobody
can accuse the other of gaming it. Each item is a fair, independent flip. They are pleased with themselves. Your job is to find out whether they
should be.

== Part 1. Predict First

Answer both of these #emph[before] you touch the coin. Write down a number, not a feeling.

#question[
  #set par(justify: false)
  1.1 The inventory below is appraised at \$120,000. How much do you expect your aunt to end
  up with? #blank(width: 3cm)
]

#question[
  #set par(justify: false)
  1.2 How far from an even split do you expect the actual settlement to land? Circle one. \
  #v(0.05cm)
  #h(0.5cm) under \$5,000 #h(0.8cm) \$5,000–15,000 #h(0.8cm) \$15,000–30,000 #h(0.8cm) over \$30,000
]

== Part 2. The Settlement

One of you is the AUNT and takes heads. One of you is the UNCLE and takes tails. Flip once
for each of the twelve items and mark the winner with *A* or *U*. Then do the whole thing a
second time, from scratch — a second settlement, in a parallel universe where the coin fell
differently.

#v(0.15cm)
#align(center)[
  #table(
    columns: (0.9cm, 6.6cm, 2.6cm, 2.1cm, 2.1cm),
    inset: 4.5pt,
    align: (center, left, right, center, center),
    stroke: 0.5pt + rgb("#888888"),
    [], [*Item*], [*Appraised value*], [*Round 1*], [*Round 2*],
    [1], [The lake cabin], [\$60,000], [], [],
    [2], [Pickup truck], [\$14,000], [], [],
    [3], [Sailboat], [\$11,000], [], [],
    [4], [Grandmother's diamond ring], [\$8,500], [], [],
    [5], [Baby grand piano], [\$7,000], [], [],
    [6], [Comic book collection], [\$5,500], [], [],
    [7], [Dining room set], [\$4,500], [], [],
    [8], [Snowblower and power tools], [\$3,500], [], [],
    [9], [Espresso machine], [\$2,500], [], [],
    [10], [Mountain bikes (pair)], [\$2,000], [], [],
    [11], [Vinyl record collection], [\$1,500], [], [],
    [12], [Bruno, the dog], [\$0], [], [],
    table.hline(stroke: 1pt),
    [], [*Total*], [*\$120,000*], [], [],
  )
]

#v(0.1cm)

#question[
  #set par(justify: false)
  2.1 Round 1 — Aunt: #blank(width: 2.6cm) #h(0.5cm) Uncle: #blank(width: 2.6cm) #h(0.5cm) Gap: #blank(width: 2.6cm) \
  #v(0.05cm)
  Round 2 — Aunt: #blank(width: 2.6cm) #h(0.5cm) Uncle: #blank(width: 2.6cm) #h(0.5cm) Gap: #blank(width: 2.6cm)
]

Report both of your aunt's totals to the board.

== Part 3. The Class Distribution

Every settlement in the room goes on the board as one mark in the bin containing the aunt's
total. Copy the finished class histogram here.

#v(0.3cm)
#align(center)[
  #table(
    columns: (1.28cm,) * 12,
    rows: (0.62cm,) * 8,
    inset: 2pt,
    align: center,
    stroke: 0.5pt + rgb("#aaaaaa"),
    ..([],) * 96,
  )
  #v(-0.05cm)
  #table(
    columns: (1.28cm,) * 12,
    inset: 2pt,
    align: center,
    stroke: none,
    ..(
      [0–10], [10–20], [20–30], [30–40], [40–50], [50–60],
      [60–70], [70–80], [80–90], [90–100], [100–110], [110–120],
    ).map(x => text(size: 7pt, x)),
  )
  #v(-0.15cm)
  #text(size: 9pt, style: "italic")[Aunt's share, thousands of dollars]
]

#v(0.3cm)

#question[
  #set par(justify: false)
  3.1 Where is the center of the class distribution? #blank(width: 3cm) \
  #v(0.05cm)
  An even split would be \$60,000. How close is the center to that?
]

#question[
  #set par(justify: false)
  3.2 Settlements within \$10,000 of even: #blank(width: 1.8cm) out of #blank(width: 1.8cm)
  #h(0.5cm) That is #blank(width: 1.8cm) percent.
]

#question[
  3.3 The histogram does not have a single hump in the middle. Describe its shape, then
  explain what feature of the inventory produces that shape.
]

#answer-space(height: 2.4cm)

#question[
  #set par(justify: false)
  3.4 Largest gap between the two parties seen anywhere in the room: #blank(width: 3cm)
]

#question[
  3.5 The average settlement is \$60,000, and \$60,000 sits in one of the emptiest parts of
  the histogram. Explain how a number can be the average of a quantity and still be an
  outcome you almost never see.
]

#answer-space(height: 2.6cm)

== Part 4. Discussion

#question[
  4.1 Each flip is fair and the procedure gives each party an expected \$60,000. Your uncle
  says that makes the settlement fair. Your aunt, holding the record collection and the
  espresso machine, disagrees. Both of them are using the word correctly. What are the two
  different things they mean by it?
]

#answer-space(height: 2.6cm)

#question[
  4.2 Bruno is appraised at \$0, and the coin treats him accordingly. Name one other item on
  the list that is probably worth very different amounts to the two of them, and say what
  the appraisal column is failing to capture.
]

#answer-space(height: 2.4cm)

#question[
  4.3 Suppose the cabin were sold first and replaced on the inventory by four items worth
  \$15,000 each. The total is unchanged and each party's expected share is still \$60,000.
  What happens to the histogram? Would you call the new procedure fairer, and in which of
  the two senses from 4.1?
]

#answer-space(height: 2.8cm)

#question[
  4.4 Propose a settlement procedure you would actually recommend to them. What does your
  procedure require from your aunt and uncle that the coin does not require?
]

#answer-space(height: 2.8cm)

#question[
  4.5 Every flip was fair, every flip was independent, and the expected shares were equal.
  So where did the unfairness come from?
]

#answer-space(height: 2.8cm)
