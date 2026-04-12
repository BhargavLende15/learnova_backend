"""
Single source of truth for static assessment MCQs.
Each item: question_id, question, options (4 strings on the same topic), correct_answer (must match one option exactly).
"""
from __future__ import annotations

import hashlib
import random
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple

from app.catalog_data import SKILLS_BY_GOAL
from app.models import SkillLevel

# skill -> list of MCQ dicts (without skill field; added when flattening)
_RAW_BANK: Dict[str, List[Dict[str, Any]]] = {}


def _mcq(qid: str, stem: str, correct: str, d1: str, d2: str, d3: str) -> Dict[str, Any]:
    return {
        "question_id": qid,
        "question": stem,
        "correct_answer": correct,
        "options": [correct, d1, d2, d3],
    }


# --- Python ---
_RAW_BANK["Python"] = [
    _mcq(
        "py_1",
        "What does a list comprehension in Python primarily let you do?",
        "Build a new list by transforming or filtering items from an iterable in one expression",
        "Declare static types for all variables in a function",
        "Replace every import statement with a namespace alias",
        "Compile Python source to native machine code before runtime",
    ),
    _mcq(
        "py_2",
        "In Python, what is the main purpose of `if __name__ == \"__main__\"`?",
        "Run certain code only when the file is executed directly, not when imported",
        "Hide private attributes from subclasses",
        "Enable async/await inside synchronous functions",
        "Register the file with pip as an installable package",
    ),
    _mcq(
        "py_3",
        "Which statement best describes a Python virtual environment (`venv`)?",
        "It isolates project dependencies from the system Python interpreter",
        "It encrypts your source files at rest",
        "It replaces the need for requirements.txt",
        "It pins your code to a single CPU core for speed",
    ),
    _mcq(
        "py_4",
        "What is a generator function in Python?",
        "A function that uses `yield` to produce values lazily, one at a time",
        "A function that always materializes the full result as a tuple",
        "A built-in that sorts dictionaries by key automatically",
        "A decorator that memoizes return values forever",
    ),
    _mcq(
        "py_5",
        "Which choice best captures duck typing in Python?",
        "You care whether an object supports the needed methods/behavior, not its declared class name",
        "Every variable must declare an explicit interface before use",
        "Types are enforced at compile time like in C",
        "Only subclasses of `object` may participate in polymorphism",
    ),
]

# --- Statistics ---
_RAW_BANK["Statistics"] = [
    _mcq(
        "stat_1",
        "What does a 95% confidence interval for a mean typically communicate?",
        "A range of plausible values for the parameter, given sampling variability and the chosen method",
        "There is a 95% chance the sample mean equals the population mean",
        "95% of all data points must fall inside the interval",
        "The p-value is exactly 0.05",
    ),
    _mcq(
        "stat_2",
        "Why is correlation between two variables not enough to prove causation?",
        "Confounders, reverse causality, or chance can produce association without direct cause",
        "Correlation is only defined for categorical variables",
        "Correlation always equals the slope of the regression line squared",
        "Scatter plots cannot display correlation",
    ),
    _mcq(
        "stat_3",
        "What does standard deviation measure in a dataset?",
        "How spread out values are around the mean",
        "The most frequent category in a distribution",
        "The difference between median and mode",
        "Whether the sample passed a normality test",
    ),
    _mcq(
        "stat_4",
        "In hypothesis testing, a small p-value (e.g. < 0.05) usually means what?",
        "The observed data would be surprising if the null hypothesis were true",
        "The alternative hypothesis is proven with certainty",
        "The experiment had no measurement error",
        "The sample size was too small to analyze",
    ),
    _mcq(
        "stat_5",
        "What is the median of a sample?",
        "The middle value when observations are ordered (or average of two middle values)",
        "The arithmetic mean divided by the sample size",
        "The most common value regardless of ordering",
        "The width of the interquartile range",
    ),
]

# --- Machine Learning ---
_RAW_BANK["Machine Learning"] = [
    _mcq(
        "ml_1",
        "What defines supervised learning?",
        "Training with input-output pairs where labels or targets are provided",
        "Training without any labels using only rewards from the environment",
        "Optimizing model size to fit in browser localStorage",
        "Choosing the best database index for feature storage",
    ),
    _mcq(
        "ml_2",
        "What is overfitting?",
        "The model fits training noise and fails to generalize to new data",
        "The model is too simple to reduce training loss",
        "The learning rate is exactly zero",
        "The validation set is larger than the training set",
    ),
    _mcq(
        "ml_3",
        "Why use a validation set during model development?",
        "Tune hyperparameters and estimate generalization without peeking at the test set",
        "Train the model with more epochs than the training set allows",
        "Replace the need for cross-validation in every project",
        "Store production user data for debugging",
    ),
    _mcq(
        "ml_4",
        "What is a common purpose of regularization (e.g. L2)?",
        "Discourage overly large weights to improve generalization",
        "Guarantee the model reaches zero training error",
        "Convert classification problems into clustering automatically",
        "Increase the number of parameters without bound",
    ),
    _mcq(
        "ml_5",
        "What does k-fold cross-validation do?",
        "Splits data into k parts, trains k times holding out one fold each time for evaluation",
        "Splits features into k clusters using k-means",
        "Runs training on k GPUs in parallel only",
        "Chooses k as the optimal number of classes",
    ),
]

# --- SQL ---
_RAW_BANK["SQL"] = [
    _mcq(
        "sql_1",
        "What does `INNER JOIN` return?",
        "Rows where the join predicate matches in both tables",
        "All rows from the left table including non-matches",
        "Only rows that appear in neither table",
        "Aggregated sums without a GROUP BY clause",
    ),
    _mcq(
        "sql_2",
        "What is a primary key constraint meant to ensure?",
        "Each row can be uniquely identified within its table",
        "Every column must allow NULL values",
        "Queries never use indexes",
        "Foreign keys are optional in all databases",
    ),
    _mcq(
        "sql_3",
        "What does `GROUP BY` enable together with aggregate functions?",
        "Compute aggregates (COUNT, SUM, …) within each group of rows sharing grouping keys",
        "Sort rows alphabetically without an ORDER BY",
        "Remove duplicate databases from the server",
        "Join more than two tables in one pass automatically",
    ),
    _mcq(
        "sql_4",
        "What is a subquery?",
        "A query nested inside another query, often in WHERE or FROM",
        "A backup copy of the entire database",
        "A synonym for PRIMARY KEY",
        "A type of index that stores JSON only",
    ),
    _mcq(
        "sql_5",
        "Why might you create an index on a column used in WHERE clauses?",
        "To speed up lookups and filters on large tables",
        "To prevent NULLs from ever appearing",
        "To encrypt values at rest automatically",
        "To duplicate every row for redundancy",
    ),
]

# --- HTML ---
_RAW_BANK["HTML"] = [
    _mcq(
        "html_1",
        "What is the main accessibility benefit of associating a `<label>` with a form control?",
        "Clicking the label focuses the control and screen readers get a proper name",
        "It encrypts the field before submission",
        "It disables browser autofill completely",
        "It replaces server-side validation",
    ),
    _mcq(
        "html_2",
        "What do semantic elements like `<article>`, `<nav>`, and `<header>` primarily communicate?",
        "Meaningful structure for assistive tech, SEO, and maintainability",
        "That CSS cannot style those elements",
        "That JavaScript is forbidden inside them",
        "That the page must be served only over HTTP/2",
    ),
    _mcq(
        "html_3",
        "What is the HTML `lang` attribute on `<html>` used for?",
        "Helps browsers and assistive technologies pick correct pronunciation and language rules",
        "Forces all text to render in monospace",
        "Blocks translation services from running",
        "Declares the server programming language",
    ),
    _mcq(
        "html_4",
        "Why is heading hierarchy (h1 → h2 → h3) important?",
        "It creates a logical outline for navigation and assistive technologies",
        "It sets font sizes that cannot be changed with CSS",
        "It limits pages to exactly three sections",
        "It is required for images to load",
    ),
    _mcq(
        "html_5",
        "What is a practical use of the `alt` attribute on `<img>`?",
        "Describe the image for screen readers and when the image fails to load",
        "Set the image as a background for the whole site",
        "Lazy-load video files instead of images",
        "Force the image to stretch to full viewport height",
    ),
]

# --- CSS ---
_RAW_BANK["CSS"] = [
    _mcq(
        "css_1",
        "What does CSS specificity determine?",
        "Which rule wins when multiple selectors target the same element",
        "How long the stylesheet file is on disk",
        "Whether flexbox or grid is allowed in a project",
        "The order JavaScript files execute",
    ),
    _mcq(
        "css_2",
        "When is Flexbox especially appropriate?",
        "One-dimensional layouts: aligning items along a row or column axis",
        "3D WebGL rendering inside a canvas",
        "Normalizing SQL schemas",
        "Signing JWT tokens in the browser",
    ),
    _mcq(
        "css_3",
        "What is the CSS `box model` composed of?",
        "Content, padding, border, and margin (in that outward order)",
        "Only width and height with no padding allowed",
        "Flex containers and grid tracks exclusively",
        "HTML tags that carry style attributes only",
    ),
    _mcq(
        "css_4",
        "What do media queries enable?",
        "Apply styles conditionally based on viewport or device features",
        "Query a SQL database from CSS",
        "Import Python modules into stylesheets",
        "Animate elements without `@keyframes`",
    ),
    _mcq(
        "css_5",
        "What is `position: sticky` useful for?",
        "Elements that behave like relative until a scroll threshold, then stay visible within a container",
        "Fixing an element to the viewport center forever regardless of scroll",
        "Hiding elements from the accessibility tree only",
        "Disabling z-index stacking",
    ),
]

# --- JavaScript ---
_RAW_BANK["JavaScript"] = [
    _mcq(
        "js_1",
        "What is a JavaScript closure?",
        "A function that retains access to variables from its enclosing lexical scope",
        "A built-in API to terminate WebSocket connections",
        "A CSS class that hides overflow",
        "A Promise that cannot be awaited",
    ),
    _mcq(
        "js_2",
        "What does the event loop primarily coordinate in the browser?",
        "Running callbacks and microtasks after the call stack clears, alongside rendering and I/O",
        "Parsing HTML synchronously on the main thread only once",
        "Compiling TypeScript to WASM automatically",
        "Managing GPU shader compilation",
    ),
    _mcq(
        "js_3",
        "How does `===` differ from `==` in typical usage?",
        "`===` checks value and type without coercion; `==` may coerce types",
        "`===` compares object references only",
        "`==` is deprecated in strict mode entirely",
        "They are identical in all JavaScript engines",
    ),
    _mcq(
        "js_4",
        "What is `async/await` primarily syntactic sugar for?",
        "Working with Promises in a linear, readable style",
        "Replacing the need for any callbacks in the language",
        "Declaring classes with private fields only",
        "Bundling npm packages for the browser",
    ),
    _mcq(
        "js_5",
        "What is the DOM?",
        "A tree representation of the document that scripts can read and update",
        "A database used by Node.js middleware",
        "A WebAssembly memory layout",
        "The same thing as the JavaScript engine bytecode",
    ),
]

# --- React ---
_RAW_BANK["React"] = [
    _mcq(
        "react_1",
        "What are props in React?",
        "Inputs passed from a parent component to configure a child component",
        "Mutable state that only child components can write",
        "CSS class names reserved by React core",
        "Server-only secrets injected at build time",
    ),
    _mcq(
        "react_2",
        "Which hook is most appropriate for side effects like data fetching or subscribing to events?",
        "useEffect",
        "useState",
        "useMemo",
        "useId",
    ),
    _mcq(
        "react_3",
        "What problem does the Virtual DOM help React address?",
        "Efficiently computing minimal updates to the real DOM",
        "Encrypting user passwords in the browser",
        "Replacing HTTP with WebSockets for all requests",
        "Storing relational data without a database",
    ),
    _mcq(
        "react_4",
        "What does `useState` return?",
        "A state value and a setter function to update it",
        "Only a boolean loading flag",
        "A ref to the root DOM node",
        "The entire Redux store",
    ),
    _mcq(
        "react_5",
        "Why split UI into components?",
        "Reuse, isolation, and easier reasoning about state and rendering",
        "Because each file must be under 50 lines",
        "To prevent using hooks in the app",
        "To disable server-side rendering",
    ),
]

# --- Node.js ---
_RAW_BANK["Node.js"] = [
    _mcq(
        "node_1",
        "What is middleware in an Express-style Node server?",
        "Functions that run in the pipeline between receiving a request and sending a response",
        "A database migration tool",
        "A React higher-order component",
        "A replacement for the V8 engine",
    ),
    _mcq(
        "node_2",
        "Why is Node.js often chosen for I/O-heavy APIs?",
        "Its non-blocking, event-driven model can handle many concurrent connections efficiently",
        "It runs Python scientific stacks natively",
        "It compiles TypeScript in the browser",
        "It replaces DNS resolution globally",
    ),
    _mcq(
        "node_3",
        "What does `npm` primarily help you do?",
        "Install and manage JavaScript packages and project dependencies",
        "Compile C++ addons only",
        "Host static files on CDN edge nodes",
        "Run only security audits without installing packages",
    ),
    _mcq(
        "node_4",
        "What is `require` / ES modules `import` used for in Node?",
        "Load other modules and reuse code across files",
        "Allocate GPU buffers for compute shaders",
        "Declare environment variables in production only",
        "Patch the Linux kernel from JavaScript",
    ),
    _mcq(
        "node_5",
        "What is a common role of `process.env` in Node apps?",
        "Read configuration like ports and secrets from the environment",
        "Spawn a new browser window",
        "Measure React render times",
        "List all open TCP ports on the internet",
    ),
]

# --- Deep Learning ---
_RAW_BANK["Deep Learning"] = [
    _mcq(
        "dl_1",
        "What does an activation function typically add to a neural network?",
        "Non-linearity so the network can represent complex functions",
        "Guaranteed convex loss surfaces",
        "Automatic database normalization",
        "Lossless compression of weights",
    ),
    _mcq(
        "dl_2",
        "What is transfer learning?",
        "Starting from a pretrained model and adapting it to a related task with less data",
        "Copying datasets between servers without training",
        "Removing all layers to reduce parameters to zero",
        "Training without any validation metric",
    ),
    _mcq(
        "dl_3",
        "What is a CNN especially suited for?",
        "Grid-like data such as images using convolutional filters",
        "Sorting relational tables in SQL",
        "Parsing JSON in Express middleware",
        "Compiling Python to WebAssembly",
    ),
    _mcq(
        "dl_4",
        "What is dropout used for during training?",
        "Randomly zeroing activations to reduce co-adaptation and overfitting",
        "Dropping the learning rate to zero permanently",
        "Removing labels from the dataset",
        "Converting classification to regression only",
    ),
    _mcq(
        "dl_5",
        "What does backpropagation compute?",
        "Gradients of the loss with respect to parameters for optimization",
        "The exact global minimum without iteration",
        "The dataset median",
        "A confusion matrix only",
    ),
]


def _flatten_for_skills(skills: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for skill in skills:
        bank = _RAW_BANK.get(skill)
        if not bank:
            continue
        for q in bank:
            item = {**q, "skill": skill, "topic": skill}
            out.append(item)
    return out


def get_flat_questions_for_skills(skills: List[str]) -> List[Dict[str, Any]]:
    """Full question rows including correct_answer (server-only)."""
    return _flatten_for_skills(skills)


def _rng_for_session(session_id: str) -> random.Random:
    h = hashlib.sha256(session_id.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "big")
    return random.Random(seed)


def prepare_public_questions(skills: List[str], session_id: str) -> List[Dict[str, Any]]:
    """Strip correct_answer and shuffle options deterministically per session."""
    rng = _rng_for_session(session_id)
    public: List[Dict[str, Any]] = []
    for q in _flatten_for_skills(skills):
        opts = list(q["options"])
        rng.shuffle(opts)
        public.append(
            {
                "question_id": q["question_id"],
                "skill": q["skill"],
                "topic": q.get("topic", q["skill"]),
                "question": q["question"],
                "options": opts,
            }
        )
    return public


def _similarity(a: str, b: str) -> float:
    a_clean = (a or "").lower().strip()
    b_clean = (b or "").lower().strip()
    if not a_clean or not b_clean:
        return 0.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def _score_to_level(score: float) -> str:
    if score < 40:
        return SkillLevel.BEGINNER.value
    if score < 70:
        return SkillLevel.INTERMEDIATE.value
    return SkillLevel.ADVANCED.value


def score_static_assessment(skills: List[str], answers: Dict[str, str]) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """
    Compute per-skill levels and raw scores from submitted answers.
    answers: question_id -> selected option text
    """
    by_skill: Dict[str, List[Dict[str, Any]]] = {}
    for q in _flatten_for_skills(skills):
        by_skill.setdefault(q["skill"], []).append(q)

    skill_levels: Dict[str, Any] = {}
    raw_scores: Dict[str, float] = {}

    for skill, qs in by_skill.items():
        correct = 0
        total = len(qs)
        for q in qs:
            qid = q["question_id"]
            sel = answers.get(qid, "").strip()
            ca = q["correct_answer"]
            if sel and _similarity(sel, ca) >= 0.55:
                correct += 1
        pct = (correct / total * 100.0) if total else 0.0
        raw_scores[skill] = round(pct, 1)
        skill_levels[skill] = {"level": _score_to_level(pct), "score": raw_scores[skill]}

    return skill_levels, raw_scores


def get_questions_for_goal(goal: str) -> List[Dict[str, Any]]:
    """Legacy / diagnostic: questions for all skills in a goal (public fields only)."""
    skills = SKILLS_BY_GOAL.get(goal, ["Python", "Statistics", "Machine Learning"])
    return [
        {
            "question_id": q["question_id"],
            "skill": q["skill"],
            "question": q["question"],
            "options": list(q["options"]),
            "topic": q.get("topic", q["skill"]),
        }
        for q in _flatten_for_skills(skills)
    ]


def get_questions_for_skills(skills: List[str]) -> List[Dict[str, Any]]:
    """Flatten question bank for selected skills (public-shaped, no correct_answer)."""
    return [
        {
            "question_id": q["question_id"],
            "skill": q["skill"],
            "question": q["question"],
            "options": list(q["options"]),
            "topic": q.get("topic", q["skill"]),
        }
        for q in _flatten_for_skills(skills)
    ]
