# NSB Toolbox

## A command-line utility for formatting Science Bowl questions

Version 0.4.2 - Updated for 2023 NSB

The NSB Toolbox contains a set of tools to make it easier to write and edit Science Bowl questions. It ensures that questions are compliant with the official Science Bowl format, allowing writers to focus on just writing the questions. It also highlights common formatting errors for editors, allowing them to focus on checking content without worrying that they're missing formatting issues here and there.

## Table of Contents

1. [Installation](#installation)
2. [Documentation](#documentation)
    1. [nsb format](#nsb-format)
        1. [Auto-Formatting](#auto-format)
        2. [Linting](#linting)
    2. [nsb assign](#nsb-assign)
        1. [Sample Configuration](#assign-config)
    3. [nsb make](#nsb-make)
3. [Known Issues](#known-issues)

<a name="installation"></a>
## Installation
Currently, the NSB Toolbox can be installed via pip from this github. To do so, you will need:

* Python 3.8 or greater installed on your computer.
* Enter and run ```pip install nsb-toolbox``` in your command line.
* Verify the installation worked by running ```nsb -h``` in your command line. If the help information for the toolbox appears, the installation was successful.

<a name="documentation"></a>
## Documentation
You can access the NSB Toolbox via the ```nsb``` commandlet. Running ```nsb -h``` displays the following help menu.

```powershell
(base) PS C:\Users\rishik> nsb -h
usage: nsb [-h] {format,make} ...

Utilities for managing Science Bowl .docx files.

optional arguments:
  -h, --help     show this help message and exit

subcommands:
  {format,make}
    format       format a Science Bowl file
    make         make a Science Bowl table
```
<a name="nsb-format"></a>
## nsb format
```nsb format``` provides two functions in one - first, it is a formatter than ensures Science Bowl questions are properly spaced (four spaces between question type and start of stem, blank line between stem and answer, etc). Second, it is a linter that highlights questions that it cannot fix. It is important to note that ```nsb format``` cannot catch every problem with the question! For example, ```nsb format``` will never be able to check question content for correctness. All ```nsb format``` can do is eliminate or highlight typical formatting errors.

### Usage

```nsb format``` takes a single argument, the path to the target .docx file. For example:

```nsb format path/to/nsb/questions.docx```

<a name="auto-format"></a>
### Auto-Formatting

```nsb format``` outright fixes a number of formatting errors. It strives to produce questions that have the following characteristics:

* The question class (TOSS-UP, BONUS) is uppercase.
* Subject (Biology, Chemistry, etc.) are title case.
* Question type (Multiple Choice, Short Answer) are italicized and title case.
* There are four spaces between the question type and the start of the stem.
* For multiple choice questions, the stem and choices are each separated by a single paragraph break.
* There are two paragraph breaks before the answer line.
* The answer line is uppercase.

Notably, `nsb format` operates by moving, copying, and inserting XML elements. This ensures that **user-provided formatting won't be overwritten** (for example, superscripts and subscripts for mathematical formulae). 

For example, all of the following improperly formatted questions:

![Before Formatting](/docs/images/before_format.png) 

```nsb format``` will automatically convert these questions to be compliant with the Science Bowl format:

![After Formatting](/docs/images/after_format.png)

Shorthand notation can also be used to reduce the amount of time writers spend writing boilerplate.

![Before Shorthand](/docs/images/before_shorthand.png)

TU and B will be converted to TOSS-UP and BONUS, respectively. The shorthand for the subject categories is the first letter of the subject, aside for Earth and Space (ES) and Energy (EN). MC and SA will be converted to Multiple Choice and Short Answer, as well.

![After Shorthand](/docs/images/after_shorthand.png)

Finally, ```nsb format``` will automatically correct minor errors in question structure. For example, the following question has multiple X) choices:

![Before Multiple Choice Correction](/docs/images/before_mc_correct.png)

The mislabeled choices will be automatically corrected. Note that an answer line that has been explicitly given will not be auto-capitalized:

![After Multiple Choice Correction](/docs/images/after_mc_correct.png)

<a name="linting"></a>
### Linting

If ```nsb format``` fails to parse a cell, it will raise linting errors by highlighting the question and printing the error in the command line. There are two levels of errors: parsing errors, which will highlight a cell red, and question structure errors, which will highlight the problematic structure yellow. `nsb format` searches for the following errors:

* The question has a class, subject, type, stem, and answer. Multiple Choice questions should also have four choices.
* Question type is correctly labeled - Multiple Choice questions should have choices, Short Answer questions should not.
* For multiple choice questions, the wording of the answer line should match the wording of the choice.

For example:

![Linter Errors](/docs/images/linter_errors.png)

The first question is missing two choices, so it can't be fully parsed, raising a red error. The second question is merely mislabeled - it says it's a Multiple Choice question, but is recognized as a Short Answer question. This raises a yellow error, highlighting the question type. Messages corresponding to these errors are printed in the terminal, as well:

```
(base) rishi@RISHI-DESKTOP:~$ nsb format after_format.docx
Question 6: Couldn't parse question, was looking for QuestionFormatterState.CHOICES
Question 7: Question type is MC, but has no choices.
```

```nsb format``` is not capable of deleting lines that contain text. This is intentional - while there are errors that ```nsb format```  highlights that it could probably fix automatically, the maintainer believes it is more prudent to leave whitespace formatting to ```nsb format``` and making any other changes by hand.

<a name="nsb-assign"></a>
## nsb assign
`nsb assign` uses a set of configuration options to automatically assign a set of edited questions to rounds. 

### Usage

```nsb assign``` takes two arguments, the path to the edited set of Science Bowl questions and the path to the configuration file. For example:

```nsb assign path/to/nsb/questions.docx -c path/to/config.yaml```

<a name="assign-config"></a>
### Sample Configuration File

Below is a sample configuration file for a High School Regional set. The sections are explained in more detail further below.

```yaml
Configuration:
  Shuffle Subcategory: True 
  Shuffle Pairs: False 
  Shuffle LOD: False
  Random Seed: ~
  Subcategory Mismatch Penalty: 1
  Preferred Writers: []

Round Definitions:
  Tiebreakers:
    TU:
      LOD: [2]

  RoundRobin:
    TU:
      LOD: [1, 1, 1, 1]
      Subcategory: [Organic, ~, ~, ~]

    B:
      LOD: [1, 1, 1, 1]
      Subcategory: [Organic, ~, ~, ~]

  DoubleElim1-4:
    TU:
      LOD: [2, 2, 2, 2]

    B:
      LOD: [2, 2, 2, 2]

  DoubleElim5-6:
    TU:
      LOD: [2, 2, 2, 2]

    B:
      LOD: [2, 2, 3, 3]

  DoubleElim7-9:
    TU:
      LOD: [2, 2, 3, 3]
    B:
      LOD: [2, 3, 3, 3]

Sets:
  - Set: [HSR]
    Prefix: RR
    Rounds: [1, 2]
    Template: RoundRobin

  - Set: [HSR]
    Prefix: TB
    Rounds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    Template: Tiebreakers

  - Set: [HSR-A, HSR-B]
    Prefix: RR
    Rounds: [3, 4, 6, 7, 8]
    Template: RoundRobin

  - Set: [HSR-A, HSR-B]
    Prefix: RR
    Rounds: [5]
    Template:
      from: RoundRobin
      add:
        TU:
          LOD: [1]
        B:
          LOD: [1]

  - Set: [HSR-A, HSR-B]
    Prefix: DE
    Rounds: [1, 2, 3, 4]
    Template: DoubleElim1-4

  - Set: [HSR-A, HSR-B]
    Prefix: DE
    Rounds: [5, 6]
    Template: DoubleElim5-6

  - Set: [HSR-A, HSR-B]
    Prefix: DE
    Rounds: [7, 8, 9]
    Template: DoubleElim7-9

```

### Configuration Options

`Shuffle Subcategory`: Setting this option to `True` randomizes the order that any subcategory specification appears in a round. For example, if you have requested `["Organic", ~, ~, ~]`, setting this option to `True` makes the `"Organic"` subcategory uniformly distributed rather than the first question of each round. Note that setting this option to `True` breaks any matching between `TU` and `B` subcategories.

`Shuffle Pairs`: Setting this option to `True` adds a randomization step after each pair of questions has been constructed. This is useful when you have intentionally matched `TU` and `B` subcategories, for example, but want to randomize the order that the subcategories appear in each round. Note that even when this is enabled, the final pair of each round will be `Short Answer` questions.

`Shuffle LOD`: Setting this option to `True` randomizes the order that question difficulties appear in each round, similar to the above options.

`Random Seed`: Setting this option to an integer fixes the generated assignment, all else being equal. If left unspecified or set to None, the assignment will have a slight random element to it.

`Subcategory Mismatch Penalty`: Setting this option to an integer specifies how much cost is incurred by creating a subcategory mismatch. Common options include: 

`1`, which says that matching a question with the right difficulty but wrong subcategory is equally costly as using a question whose difficulty is off by `1`, but the subcategory is correct. 

`2`, which says that matching a question with the right difficulty but wrong subcategory is always less preferable than using a question with the right subcategory but off-by-one difficulty, but also always more preferable than using a question with the right subcategory but off-by-two difficulty.

`Preferred Writers`: If specified, any writers NOT in this list are given a small penalty, encouraging the optimization algorithm to use the preferred writers. This penalty is very small and should never result in a question of the wrong subcategory or difficulty from a preferred writer being used over a question of the right subcategory and difficulty from an unpreferred writer.

### Round Definitions

```yaml
Round Definitions:
  Tiebreakers:
    TU:
      LOD: [2]

  RoundRobin:
    TU:
      LOD: [1, 1, 1, 1]
      Subcategory: [Organic, ~, ~, ~]
    B:
      LOD: [1, 1, 1, 1]
      Subcategory: [Organic, ~, ~, ~]
```

`Round Definitions` serve as templates to build round specifications. Each round definition needs to specify the question types it uses (`TU` and/or `B` for TOSS-UP and BONUS) and the Level of Difficulty of each question. Optionally, the subcategories can be specified. Entering a `~` indicates that there is no subcategory preference for that slot.

To explain the above specification in plain English, we want all Tiebreaker rounds to consist of a single
TOSS-UP question with a difficulty of 2, and all Round Robin rounds to consist of 4 TOSS-UPs and 4 BONUSes that each have a difficulty of 1. Finally, a quarter of TOSS-UPs and BONUSes should use the "Organic" subcategory.

### Sets

```yaml
Sets:
  - Set: [HSR-A, HSR-B]
    Prefix: RR
    Rounds: [1, 2]
    Template: RoundRobin
```

The `Sets` section actually specifies what rounds will be built. A set is defined with the `Set`, `Prefix`, `Rounds`, and `Template` keys. The `Set`, `Prefix`, and `Rounds` keys are round meta-data, while the `Template` key will build the round using the matching entry in the `Round Specifications` section. 

These keys are used combinatorially - the above set will generate 4 rounds: HSR-A RR1, HSR-A RR2, HSR-B RR1, and HSR-B RR2. 

Optionally, `Sets` can use the `from:`, `add:` syntax:

```yaml
  - Set: [HSR-A, HSR-B]
    Prefix: RR
    Rounds: [5]
    Template:
      from: RoundRobin
      add:
        TU:
          LOD: [1]
        B:
          LOD: [1]
```
This syntax specifies that the `RoundRobin` template should be used, but there should be an extra TOSS-UP and BONUS that each have a difficulty of 1.

<a name="nsb-make"></a>
## nsb make
```nsb make``` produces a blank Science Bowl question table with a designated number of lines. This is a convenience function for writers. ```nsb make -h``` shows the following help menu:

```powershell
(base) PS C:\Users\rishik> nsb make -h
usage: nsb make [-h] [-n NAME] [-st {HSR,HSN,MSR,MSN}] [-su {B,C,P,M,ES,EN}] path rows

positional arguments:
  path                  path to the Science Bowl docx file
  rows                  number of rows in output table

options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Last, First name of author
  -st {HSR,HSN,MSR,MSN}, --set {HSR,HSN,MSR,MSN}
                        Set
  -su {B,C,P,M,ES,EN}, --subj {B,C,P,M,ES,EN}
                        Subject
```

For example, to create a table for 120 high school regional Physics questions for author: "Kulkarni, Rishi" the following command would work:

```powershell 
nsb make -n "Kulkarni, Rishi" -st HSR -su P Kulkarni_HS_Physics_Regionals 120
```

<a name="known-issues"></a>
## Known Issues

* If ```nsb format``` is used on a document with tracked changes, it will assume the changes were accepted. 

Please report any other issues you find on [Github](https://github.com/rishi-kulkarni/nsb-toolbox).
