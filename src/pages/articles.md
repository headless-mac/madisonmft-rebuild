---
layout: layouts/base.njk
title: Articles
permalink: /articles/
---

<div class="prose">
  <h1>Articles</h1>
  <p>Thoughts, resources, and reflections.</p>

  <ul>
  {% for post in collections.posts | reverse %}
    <li>
      <a href="{{ post.url | url }}">{{ post.data.title }}</a>
      {% if post.data.date %}<span class="kicker"> — {{ post.data.date.toISOString().slice(0,10) }}</span>{% endif %}
    </li>
  {% endfor %}
  </ul>
</div>
