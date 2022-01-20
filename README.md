# NSB Toolbox

## A command-line utility for formatting Science Bowl questions

Version 0.1

The NSB Toolbox contains a set of tools to make it easier to write and edit Science Bowl questions. It ensures that questions are compliant with the official Science Bowl format, allowing writers to focus on just writing the questions. It also highlights common formatting errors for editors, allowing them to focus on checking content without worrying that they're missing formatting issues here and there.

## Table of Contents

1. [Installation](#installation)
2. [Documentation](#documentation)
    1. [nsb format](#nsb-format)
    2. [nsb make](#nsb-make)


<a name="installation"></a>
## Installation
Currently, the NSB Toolbox can be installed via pip from this github. To do so, you will need:

* Python 3.8 or greater installed on your computer.
* Enter and run ```pip install git+https://github.com/rishi-kulkarni/nsbtoolbox.git``` in your command line.
* Verify the installation worked by running ```nsb -h``` in your command line. If the help information for the toolbox appears, the installation was successful.

<a name="documentation"></a>
## Documentation
You can access the NSB Toolbox via the ```nsb``` commandlet. Running ```nsb -h``` displays the following help menu.

```
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
### nsb format
```nsb format``` provides two functions in one - first, it is a formatter than ensures Science Bowl questions are properly spaced (four spaces between question type and start of stem, blank line between stem and answer, etc). Second, it is a linter that highlights questions that it cannot fix. It is important to note that ```nsb format``` cannot catch every problem with the question! For example, ```nsb format``` will never be able to check question content for correctness. All ```nsb format``` can do is eliminate or highlight typical formatting errors.

```nsb format``` is not capable of deleting lines that contain text. This is intentional - while there are errors that ```nsb format```  highlights that it could probably fix automatically, the maintainer believes it is more prudent to leave whitespace formatting to ```nsb format``` and making any other changes by hand.

<a name="nsb-make"></a>
### nsb make
```nsb make``` produces a blank table for writing Science Bowl questions with a designated number of lines. This is a convenience function for writers. 
