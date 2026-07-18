import pandas as pd

data = [
    {
        "Date": "2023-10-15",
        "Category": "Engineering",
        "Decision": "Migrate backend from Express.js to FastAPI for better performance.",
        "People Involved": "Alice Johnson, Bob Smith",
        "Impact": "High - Reduced API latency by 40%",
        "Alternatives Considered": "Django, Go"
    },
    {
        "Date": "2024-01-10",
        "Category": "Finance",
        "Decision": "Approve $50k budget for Q1 marketing campaign.",
        "People Involved": "Charlie Davis",
        "Impact": "Medium - Increased budget by 10%",
        "Alternatives Considered": "Maintain current budget"
    },
    {
        "Date": "2024-02-22",
        "Category": "Product",
        "Decision": "Deprecate the legacy file upload system and enforce strict S3 limits.",
        "People Involved": "Dana Lee, Alice Johnson",
        "Impact": "Medium - May cause friction for older users",
        "Alternatives Considered": "Keep both systems active"
    },
    {
        "Date": "2024-03-05",
        "Category": "HR",
        "Decision": "Switch to remote-first policy permanently.",
        "People Involved": "Evan Wright, Charlie Davis",
        "Impact": "High - Decreased office costs, improved employee retention",
        "Alternatives Considered": "Hybrid 3 days/week"
    }
]

df = pd.DataFrame(data)
df.to_excel("sample_decisions.xlsx", index=False)
print("sample_decisions.xlsx created successfully in the recallAi folder.")
