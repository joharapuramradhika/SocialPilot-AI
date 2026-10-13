def validate_content(content, products, brand):

    caption = content["caption"].lower()

    problems = []

    # Safety check
    restricted_words = [
        "hate",
        "violence",
        "adult",
        "kill",
        "weapon"
    ]

    for word in restricted_words:
        if word in caption:
            problems.append(
                f"Restricted content detected: {word}"
            )

    # Unsupported claim check
    risky_words = [
        "guaranteed",
        "100%",
        "best in the world",
        "number one",
        "zero cost"
    ]

    for word in risky_words:
        if word in caption:
            problems.append(
                f"Potentially unsupported claim: {word}"
            )

    # Product verification
    product_name = content["product"]

    valid_product = False

    for product in products:
        if product["name"] == product_name:
            valid_product = True

            allowed_features = [
                feature.lower()
                for feature in product["features"]
            ]

            if content["topic"].lower() not in allowed_features:
                problems.append(
                    "Topic is not present in approved product information."
                )

    if not valid_product:
        problems.append("Product is not approved.")

    # Final decision
    if problems:

        return {
            "status": "FAIL",
            "problems": problems
        }

    return {
        "status": "PASS",
        "problems": []
    }