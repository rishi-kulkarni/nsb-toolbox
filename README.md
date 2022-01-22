# NSB Toolbox

## A command-line utility for formatting Science Bowl questions

Version 0.1

The NSB Toolbox contains a set of tools to make it easier to write and edit Science Bowl questions. It ensures that questions are compliant with the official Science Bowl format, allowing writers to focus on just writing the questions. It also highlights common formatting errors for editors, allowing them to focus on checking content without worrying that they're missing formatting issues here and there.

## Table of Contents

1. [Installation](#installation)
2. [Documentation](#documentation)
    1. [nsb format](#nsb-format)
        1. [Auto-Formatting](#auto-format)
        2. [Linting](#linting)
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

## Usage

```nsb format``` takes a single argument, the path to the target .docx file. For example:

```nsb format path/to/nsb/questions.docx```

<a name="auto-format"></a>
## Auto-Formatting

```nsb format``` outright fixes a number of formatting errors. It strives to produce questions that have the following characteristics:

* The question class (TOSS-UP, BONUS) is uppercase.
* Subject (Biology, Chemistry, etc.) are title case.
* Question type (Multiple Choice, Short Answer) are italicized and title case.
* There are four spaces between the question type and the start of the stem.
* For multiple choice questions, there are two paragraph breaks between the stem and the first choice.
* For multiple choice questions, there is a single paragraph break between each choice.
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

The mislabeled choices will be automatically corrected:

![After Multiple Choice Correction](/docs/images/after_mc_correct.png)

<a name="linting"></a>
## Linting

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