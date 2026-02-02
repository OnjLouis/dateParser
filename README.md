<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Date Parser - NVDA Add-on Help</title>
  <style>
    body { font-family: sans-serif; line-height: 1.55; margin: 1rem; max-width: 60rem; }
    h1, h2, h3 { margin-top: 1.2rem; }
    code, kbd { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
    kbd { padding: 0.1rem 0.35rem; border: 1px solid #888; border-radius: 0.25rem; }
    ul { margin-top: 0.25rem; }
    .examples code { display: inline-block; padding: 0.05rem 0.25rem; background: #f3f3f3; border-radius: 0.2rem; }
    .note { background: #f7f7f7; border-left: 4px solid #999; padding: 0.6rem 0.8rem; }
  </style>
</head>
<body>
  <h1>Date Parser</h1>

  <p>
    Date Parser lets you type a date (or a plain-English date expression) and get back the resolved calendar date.
    Results are shown in a copy-friendly dialog with a read-only edit field.
  </p>

  <h2>Shortcut</h2>
  <p>
    Press <kbd>NVDA</kbd>+<kbd>E</kbd> to open the input dialog.
  </p>

  <h2>What you can type</h2>

  <h3>Everyday words</h3>
  <ul class="examples">
    <li><code>today</code></li>
    <li><code>tomorrow</code></li>
    <li><code>yesterday</code></li>
  </ul>

  <h3>Weekdays</h3>
  <p>
    Type a weekday name or abbreviation. If you type a weekday by itself (for example <code>mon</code>),
    Date Parser assumes you mean the next occurrence of that day (including today if it matches).
  </p>
  <ul class="examples">
    <li><code>mon</code>, <code>tuesday</code>, <code>fri</code></li>
    <li><code>next thu</code>, <code>last wed</code>, <code>this monday</code></li>
  </ul>

  <h3>Repeating weekdays</h3>
  <p>
    Ask for the Nth occurrence of a weekday in the past or future. Numbers can be digits, words, or ordinals.
  </p>
  <ul class="examples">
    <li><code>three tuesdays from now</code></li>
    <li><code>33 wednesdays ago</code></li>
    <li><code>3rd tue from now</code></li>
    <li><code>2 fri ago</code></li>
  </ul>

  <h3>Relative offsets (compact)</h3>
  <p>
    You can type compact relative offsets using:
    <strong>y</strong> (years), <strong>m</strong> (months), <strong>w</strong> (weeks), <strong>d</strong> (days).
    This works well across language boundaries because it relies on numbers and unit letters.
  </p>
  <ul class="examples">
    <li><code>5d</code>, <code>-5d</code>, <code>+5d</code></li>
    <li><code>3d ago</code>, <code>2w from now</code></li>
    <li><code>1y</code>, <code>6m</code>, <code>15w</code></li>
    <li><code>5y 4m 3w 2d</code></li>
    <li><code>5y 4m 3w 2d ago</code></li>
  </ul>
  <div class="note">
    <strong>Note:</strong> If you type a number with <code>m</code> (for example <code>5m</code>), it means <em>months</em>.
    To refer to Monday, type <code>mon</code> (not <code>m</code>).
    For named months in calendar dates, type <code>Mar</code>/<code>March</code>, e.g. <code>5 March</code> or <code>Mar 5</code>.
  </div>

  <h3>Calendar dates</h3>
  <p>
    Date Parser supports ISO format and friendly month-name formats:
  </p>
  <ul class="examples">
    <li><code>1992-09-01</code></li>
    <li><code>13 Apr 2026</code>, <code>13 April 2026</code></li>
    <li><code>5 Mar</code>, <code>5 March 2026</code></li>
    <li><code>Mar 5</code>, <code>March 5 2026</code></li>
  </ul>
  <p>
    If you omit the year, Date Parser chooses a sensible year: it will use the current year if the date
    has not happened yet, otherwise it will use next year.
  </p>

  <h2>Understanding the result</h2>
  <ul>
    <li><strong>Resolved date</strong>: the calendar date that matches your input</li>
    <li><strong>Relation</strong>: how far in the past or future it is (years, months, weeks, days)</li>
    <li><strong>Day offset</strong>: the total number of days from today (shown when not already explicit)</li>
  </ul>

  <h2>Copying and closing</h2>
  <ul>
    <li>The result text is in a read-only edit field so you can copy it.</li>
    <li>Press <kbd>Ctrl</kbd>+<kbd>C</kbd> to copy selected text.</li>
    <li>Press <kbd>Enter</kbd> or <kbd>Escape</kbd> to close the dialog.</li>
  </ul>
</body>
</html>
