# InContext

An extensible multimedia static site generator

## Background

Most existing static site generators do a great job with text content, but treat media as an afterthought. InContext handles Markdown just as well as generators like [Jekyll](https://jekyll.rb), and adds native support for photos and video. Adding support for additional media types is simply a matter of adding a new handler.

## Installation

1. [Install Docker](https://docs.docker.com/engine/install/)
2. Clone the repository:
   ```bash
   git clone git@github.com:jbmorley/incontext.git
   ```
3. Add InContext to your path:
   ```bash
   export PATH=$PATH:/path/to/incontext
   ```

## Getting Started

```bash
incontext build
```

## Frontmatter

InContext has a few special Frontmatter properties.

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

### Additional Filters

InContext provides a number of additional Jinja2 filters and context functions to make certain tasks easier.

#### Now

```
{% set d = now() %}
{{ d }}
```

Return the current date in UTC (with timezone).

#### Date

```
{% set d = date("1982-12-28") %}
{{ d }}
```

Initialize a date (with timezone) corresponding with a specific string representation.

#### Generate UUID

```
{% set uuid = generate_uuid() %}
{{ uuid }}
```

Return a new UUID.

`generate_uuid` is intended to make it easy to generate unique identifiers when writing inline HTML and JavaScript.

