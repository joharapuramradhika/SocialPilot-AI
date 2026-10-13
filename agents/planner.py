
def create_plan(products):
    """
    Creates a simple content plan using approved product data.
    """

    if not products:
        raise ValueError("No products found in products.json")

    # Support either a list of products or a dictionary
    if isinstance(products, dict):
        product_list = products.get("products", [])
    else:
        product_list = products

    if not product_list:
        raise ValueError("No products available for planning")

    product = product_list[0]

    features = product.get("features", [])

    if not features:
        raise ValueError(
            "The selected product has no approved features"
        )

    return {
        "product": product["name"],
        "topic": features[0],
        "goal": "Create an informative social media post",
        "platform": "Instagram"
    }