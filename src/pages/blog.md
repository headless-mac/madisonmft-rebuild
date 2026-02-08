---
layout: layouts/base.njk
title: Blog
permalink: /blog/
description: Thoughts, resources, and reflections.
noProse: true
---

<section class="blog">
  <div class="blog-grid">
    {% for post in collections.posts | reverse %}
      {% if not post.data.draft %}
        {% include "partials/post-card.njk" %}
      {% endif %}
    {% endfor %}
  </div>
</section>
