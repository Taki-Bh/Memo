---
name: html-parser
description: This skill should be used when the user wants to parse a webpage to extract only its raw HTML structure, clean up a webpage into an HTML skeleton, or strip out scripts and stylesheets to keep just the core HTML elements.
---

## Overview

Parses a given webpage or URL and extracts its raw HTML structure, removing unnecessary metadata, scripts, or unwanted tags as requested, and outputs the clean HTML skeleton.

## Steps

1. **Retrieve Content**: Fetch the HTML content of the target webpage URL.
2. **Clean & Strip**: Remove unwanted elements such as `<script>`, `<style>`, and tracker objects if specified, while retaining the core hierarchical HTML tags (`<div>`, `<p>`, `<a>`, headings, etc.).
3. **Format**: Structure the output nicely as a clean, readable HTML string.
4. **Output**: Return the resulting HTML structure to the user.