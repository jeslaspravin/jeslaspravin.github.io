---
layout: single
title:  "First Blog, Yay!!"
date:   2022-01-13 22:00:00 +0100
categories: general
header:
---
## 2022

It is year ***2022*** and my resolution for this year is to write blogs about my day to day events/learning or if something interesting happens. I wanted to really do this atleast this time. Yes this time, I have been trying to have my own blog for atleast past 3 years and now It is finally happening.

## Start blogging

My initial thought was to have blog integrated into [my webpage] however I do not want to create blog and also worry about scripts and styles. Then I remembered that [github-pages] seems to be cost and time effective options, So I went on checking about it and soon I realized that I have to do the same scripting and styling. It was at this point I stumbled upon static html file generators one of which is [jekyll] and I was surprised at number theme prebuilt and ready to go with this generator.

![image-right](/assets/images/First-Blog/Webpage-Blog-Filter.png){: .align-right style="border-radius: 10px;" }
Now that I worked out a target, I gathered energy to update my website to include a blog redirectors and some filters to blogs list. These redirectors will be containing a short summary of the blog content. I familiarized/refreshed myself again with `typescript`, `css`, and other static page related concepts. Also I understood `Observables` in typescript little better than last time. I setup my personal machine with environment and began rewriting my code. Following improvement or changes I did to my webpage code.
* Improved service typescripts to better cache responses
* Improved production and development builds and configurations
* Updated `google universal analytics` to `google gtags analytics`
* Done various minor improvements
* Added new Blogs page to list blogs
* Filterable blogs list with route stored filter states

Now my webpage is updated to provide a short summary on all blogs that I am going to create in [my blogs page]. In order to get [jekyll] up and running I had to do following steps
* Install `Ruby with devkit`
* Setup MSys in `Ruby` setup
* Install `bundler` and `jekyll`
* Create `jekyll` project using `jekyll new <ProjectName>`
* Tried few different themes and finally settled with gem-themes

After creating first `jekyll` project it is very straight forward to add `markdown` posts and that brings us to this **my first blog post**.

## What happens next?
I am sincerely planning to create more such a blog posts. Right now I have in mind to post only blogs related to some exciting new knowledge or events that I come across.

***`I hope you have a wonderful day`***

***`Jeslas Pravin`***{: style="color: green;" }

[//]: # (Below are link reference definitions)
[my webpage]: http://jeslaspravin.com
[my blogs page]: https://jeslaspravin.github.io
[github-pages]: https://pages.github.com/
[jekyll]: https://jekyllrb.com/