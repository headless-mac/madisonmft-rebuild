export default function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });

  eleventyConfig.addFilter("year", () => String(new Date().getFullYear()));

  return {
    dir: {
      input: "src",
      includes: "_includes",
      output: "_site"
    },
    // GitHub Pages project site base path
    pathPrefix: "/madisonmft-rebuild/",
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk"
  };
}
