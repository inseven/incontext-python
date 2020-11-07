# InContext

An extensible multimedia static site generator

## Requirements

Since there are a significant number of external dependencies (e.g., ImageMagick, FFMPEG, etc), Docker is the recommended mechanism for running builds.

1. Install [Docker](https://docs.docker.com/engine/install/ubuntu/) and Docker Compose.
2. Perform builds using `incontext-docker` instead of directly; this will run builds inside a suitably configured Ubuntu 20.04 Docker container.

## Frontmatter and Templates

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
