"""Diagnostic assessment questions for skill evaluation."""
from typing import List, Dict

# Format: { skill: [ { question_id, question, correct_answer } ] }
ASSESSMENT_QUESTIONS: Dict[str, List[Dict]] = {
    "Python": [
        {"question_id": "py_1", "question": "What is list comprehension?", "correct_answer": "A concise way to create lists from iterables"},
        {"question_id": "py_2", "question": "What is OOP (Object-Oriented Programming)?", "correct_answer": "A paradigm based on objects containing data and methods"},
        {"question_id": "py_3", "question": "What is a Python decorator?", "correct_answer": "A function that modifies another function's behavior"},
        {"question_id": "py_4", "question": "What does 'pip' do?", "correct_answer": "Package installer for Python"},
        {"question_id": "py_5", "question": "What is the difference between list and tuple?", "correct_answer": "Lists are mutable, tuples are immutable"},
    ],
    "Statistics": [
        {"question_id": "stat_1", "question": "What is mean, median, and mode?", "correct_answer": "Measures of central tendency"},
        {"question_id": "stat_2", "question": "What is standard deviation?", "correct_answer": "Measures spread of data around the mean"},
        {"question_id": "stat_3", "question": "What is p-value?", "correct_answer": "Probability of observed result under null hypothesis"},
        {"question_id": "stat_4", "question": "What is correlation vs causation?", "correct_answer": "Correlation doesn't imply causation"},
        {"question_id": "stat_5", "question": "What is a normal distribution?", "correct_answer": "Bell-shaped symmetric probability distribution"},
    ],
    "Machine Learning": [
        {"question_id": "ml_1", "question": "What is supervised learning?", "correct_answer": "Learning from labeled data with known outputs"},
        {"question_id": "ml_2", "question": "What is overfitting?", "correct_answer": "Model performs well on training but poorly on new data"},
        {"question_id": "ml_3", "question": "What is cross-validation?", "correct_answer": "Technique to assess model generalization"},
        {"question_id": "ml_4", "question": "What is a neural network?", "correct_answer": "Computing system inspired by biological neurons"},
        {"question_id": "ml_5", "question": "What is gradient descent?", "correct_answer": "Optimization algorithm to minimize loss function"},
    ],
    "SQL": [
        {"question_id": "sql_1", "question": "What does SELECT do?", "correct_answer": "Retrieves data from database tables"},
        {"question_id": "sql_2", "question": "What is a JOIN?", "correct_answer": "Combines rows from two or more tables"},
        {"question_id": "sql_3", "question": "What is GROUP BY?", "correct_answer": "Groups rows with same values for aggregate functions"},
        {"question_id": "sql_4", "question": "What is an index?", "correct_answer": "Data structure to speed up queries"},
        {"question_id": "sql_5", "question": "What is a subquery?", "correct_answer": "Query nested inside another query"},
    ],
    "React": [
        {"question_id": "react_1", "question": "What is a component?", "correct_answer": "Reusable piece of UI"},
        {"question_id": "react_2", "question": "What is useState?", "correct_answer": "Hook for state in functional components"},
        {"question_id": "react_3", "question": "What is useEffect?", "correct_answer": "Hook for side effects and lifecycle"},
        {"question_id": "react_4", "question": "What is props?", "correct_answer": "Data passed from parent to child"},
        {"question_id": "react_5", "question": "What is Virtual DOM?", "correct_answer": "Lightweight copy of DOM for efficient updates"},
    ],
    "JavaScript": [
        {"question_id": "js_1", "question": "What is closure?", "correct_answer": "Function that retains access to outer scope"},
        {"question_id": "js_2", "question": "What is async/await?", "correct_answer": "Syntax for handling Promises"},
        {"question_id": "js_3", "question": "What is the event loop?", "correct_answer": "Mechanism for handling async operations"},
        {"question_id": "js_4", "question": "What is hoisting?", "correct_answer": "Variables/functions moved to top before execution"},
        {"question_id": "js_5", "question": "What is this keyword?", "correct_answer": "Refers to the object executing the function"},
    ],
    "Deep Learning": [
        {"question_id": "dl_1", "question": "What is a CNN?", "correct_answer": "Convolutional Neural Network for image processing"},
        {"question_id": "dl_2", "question": "What is backpropagation?", "correct_answer": "Algorithm for training neural networks"},
        {"question_id": "dl_3", "question": "What is an activation function?", "correct_answer": "Introduces non-linearity to the network"},
        {"question_id": "dl_4", "question": "What is transfer learning?", "correct_answer": "Using pre-trained model for new task"},
        {"question_id": "dl_5", "question": "What is dropout?", "correct_answer": "Regularization technique to prevent overfitting"},
    ],
    "HTML": [
        {"question_id": "html_1", "question": "What does DOCTYPE do?", "correct_answer": "Declares document type for browser"},
        {"question_id": "html_2", "question": "What is semantic HTML?", "correct_answer": "Elements that convey meaning (header, nav, etc)"},
        {"question_id": "html_3", "question": "What is the box model?", "correct_answer": "Content, padding, border, margin"},
        {"question_id": "html_4", "question": "What is accessibility (a11y)?", "correct_answer": "Making web usable for people with disabilities"},
        {"question_id": "html_5", "question": "What is responsive design?", "correct_answer": "Design that adapts to different screen sizes"},
    ],
    "CSS": [
        {"question_id": "css_1", "question": "What is Flexbox?", "correct_answer": "Layout model for flexible item arrangement"},
        {"question_id": "css_2", "question": "What is Grid?", "correct_answer": "2D layout system with rows and columns"},
        {"question_id": "css_3", "question": "What is specificity?", "correct_answer": "How browsers determine which CSS rule applies"},
        {"question_id": "css_4", "question": "What is BEM?", "correct_answer": "Block Element Modifier naming convention"},
        {"question_id": "css_5", "question": "What are CSS variables?", "correct_answer": "Custom properties for reusable values"},
    ],
    "Node.js": [
        {"question_id": "node_1", "question": "What is npm?", "correct_answer": "Package manager for Node.js"},
        {"question_id": "node_2", "question": "What is Express?", "correct_answer": "Web framework for Node.js"},
        {"question_id": "node_3", "question": "What is middleware?", "correct_answer": "Functions that execute between request and response"},
        {"question_id": "node_4", "question": "What is async I/O?", "correct_answer": "Non-blocking input/output operations"},
        {"question_id": "node_5", "question": "What is the event loop in Node?", "correct_answer": "Handles async callbacks and I/O"},
    ],
}


def get_questions_for_goal(goal: str) -> List[Dict]:
    """Get assessment questions based on career goal."""
    goal_skill_map = {
        "Data Scientist": ["Python", "Statistics", "Machine Learning", "SQL"],
        "Web Developer": ["HTML", "CSS", "JavaScript", "React", "Node.js"],
        "AI Engineer": ["Python", "Machine Learning", "Deep Learning", "SQL"],
    }
    skills = goal_skill_map.get(goal, ["Python", "Statistics", "Machine Learning"])
    questions = []
    for skill in skills:
        if skill in ASSESSMENT_QUESTIONS:
            for q in ASSESSMENT_QUESTIONS[skill]:
                questions.append({**q, "skill": skill})
    return questions
