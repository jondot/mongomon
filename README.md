![](media/cover.png)

# mongomon

A Python mongodb monitor and profiler for development.


## Quick Start

Install using pip/pipenv/etc. (we recommend [poetry](https://github.com/sdispater/poetry) for sane dependency management):

```
$ poetry add mongomon --dev
```

Initialize before you set up your MongoDB connection:

```py
from mongomon import Monitor, Config
Monitor(Config(file_capture=".*/(wiki.*)")).monitor()
```

Use `file_capture` to specify how to extract relevant project file paths from traces, rather than absolute file paths.

## Exploring the Example
![](/media/demo.gif)

We've taken the example from [Flask-PyMongo](https://flask-pymongo.readthedocs.io/en/latest/) to show how easy it is to have mongomon integrated and running.

You can [look at the integration here](examples/wiki). To run it:

```
$ poetry shell
$ cd examples/wiki && pip install -r requirements
$ python wiki.py
```


## Configuration

Your main configuration points for mongomon are:

* `file_capture` - an aesthetic configuration point for capturing files for your project. Usually of the form `.*/(your-project.*)`, content in parenthesis are a regular expression capture group, and is what we actually extract.
* `low_watermark_us` - a threshold in microseconds (us) above which mongomon starts working (yellow).
* `high_watermark_us` - a high threshold in microseconds (us) above which mongomon displays timing as alert (red).


Rest of configuration looks like so (with their defaults and comments):
```py
    # cleans up stack trace with uninteresting things. Usually packages, standard library, etc.
    ignores = attrib(
        default=[
            ".*/site-packages/.*",
            ".*traceback.format_stack.*",
            r".*/lib/python\d\.\d+/.*",
        ]
    )
    # shows a file, cleans up absolute path to a file
    file_capture = attrib(default="(.*)")
    # above this value mongomon starts working
    low_watermark_us = attrib(default=5000)
    # above this value mongomon flags as alert
    high_watermark_us = attrib(default=40000)
    # customize how mongodb query looks like before printing to screen
    query_filter = attrib(default=identity)
    # want to print to something else? replace this
    print_fn = attrib(default=print_)
    # want shorter stack traces? customize this
    stack_preprocess = attrib(default=trim_last)
```

### Thanks:

To all [Contributors](https://github.com/jondot/mongomon/graphs/contributors) - you make this happen, thanks!

# Copyright

Copyright (c) 2019 [@jondot](http://twitter.com/jondot). See [LICENSE](LICENSE.txt) for further details.