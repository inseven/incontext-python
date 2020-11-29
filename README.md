# InContext

![Build](https://github.com/jbmorley/incontext/workflows/Build/badge.svg)

An extensible multimedia static site generator

## Background

Most existing static site generators do a great job with text content, but treat media as an afterthought. InContext handles Markdown just as well as generators like [Jekyll](https://jekyll.rb), and adds native support for photos and video. Adding support for additional media types is simply a matter of adding a new handler.

## Installation

1. [Install Docker](https://docs.docker.com/engine/install/)
2. Clone the repository:
   ```bash
   git clone git@github.com:inseven/incontext.git
   ```
3. Add InContext to your path:
   ```bash
   export PATH=$PATH:/path/to/incontext
   ```

## Getting Started

```bash
incontext build
```

## Front Matter

InContext has a few special Front Matter properties.

### Include

By convention, collection templates are expected to use the `include` property to determine which document categories are included.

For example,

```yaml
include:
  - posts
  - photos
```

### Exclude

By convention, collection templates are expected to use the `exclude` property to determine which document categories should be excluded.

For example,

```yaml
exclude:
  - drafts
  - screenshots
```

### Sort

Collection templates make use of the `sort` property to determine the date-based sort order of content.

For example,

```yaml
sort: ascending
```

or,

```yaml
sort: descending
```

## Templates

InContext uses [Jinja2](https://jinja.palletsprojects.com/en/2.11.x/) for templating with some additional custom filters. Check out the Jinja2 [Template Designer Documentation](https://jinja.palletsprojects.com/en/2.11.x/templates/) for basic usage.

## History

InContext is named after a Perl static site generator I wrote in 2005 (and [failed to publish](https://jbmorley.co.uk/posts/2005-06-24-incontext/)). Back then, every piece of software I wrote was named with the 'In' prefix in keeping with my [in7.co.uk](https://in7.co.uk) domain name (e.g., [InJapan](https://github.com/jbmorley/injapan), [InModem](https://github.com/jbmorley/InModem)). Hopefully this is more widely useful than my first attempt.

[InSeven Limited](https://inseven.co.uk) is still the name of my company.
