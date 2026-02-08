---
layout: layouts/base.njk
title: Blog
permalink: /blog/
description: Thoughts, resources, and reflections.
---

<p class="page-intro">Thoughts, resources, and reflections.</p>

  <ul>
  {% for post in collections.posts | reverse %}
    {% if not post.data.draft %}
      <li>
        <a href="{{ post.url | url }}">{{ post.data.title }}</a>
        {% if post.data.date %}<span class="kicker"> — {{ post.data.date.toISOString().slice(0,10) }}</span>{% endif %}
      </li>
    {% endif %}
  {% endfor %}
  </ul>
