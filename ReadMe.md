# Some helpful comments for my use

## Dev server

```sh
bundle exec jekyll serve

# In cmd(Does not works on PS)
# set JEKYLL_ENV=production
bundle exec jekyll serve
```

## Notes on minimal mistakes

* To understand more about various config used check the `minimal mistake` config.yaml
* To find more options and tags check `includes` folder and refer <https://github.com/mmistakes/minimal-mistakes/blob/master/_includes/analytics.html> to get an understanding
* To add Table of content to a page enable `toc` flag in page

```yaml
toc: true
toc_label: "My Table of Contents"
toc_icon: "cog"
```

## Kramdown

* All kramdown specific tricks works here as well
* In kramdown you can use `{: Any html tag attributes}` will be used as generated tag's attribute
* Table of content can be created using

    ```markdown
    - TOC
    {:toc}

    1. TOC
    {:toc}
    ```
