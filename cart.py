import sqlite3

class HTTPResponse(object):
    def __init__(self, status_code, body, mimetype="text/html"):
        self.status_code = status_code
        self.body = body
        self.mimetype = mimetype
        # ... additional properties omitted ...

    # ... omitted ...


class Cart(object):
    """ A user's shopping cart.
        
        ``.items``: a list of item IDs in the cart.
        ``.item_quantities``: a dictionary mapping itemIDs to the number
            of that item in the cart.
        ``.discounts``: a list of item-pair discounts that apply to this cart
            in the form ``(discount_name, discount_amount)``.
        ... additional properties omitted ...
    """

    # ... omitted ...


class Template(object):
    """ Template renderer.
        >>> Template("Hello, {{ what }}!").render({ "what": "world" })
        'Hello, world!'
    """

    # ... omitted ...


class AddItemToCartView(object):
    """ Handles requests to `/cart/add?item_id=$id&quantity=$quantity`, adding
        `quantity` of `item_id` to the current user's shopping cart.
        If the item already exists in in the cart, the quantity is updated.
        Checks to see if the cart contains any item combinations which result
        in special deals.
        Returns an "added to cart" page, confirming the name of the item which
        has been added, as well as the current quantity and messages about
        any special discounts. """

    def __init__(self, settings):
        self.settings = settings

    def handle_GET(self, request):
        item_id = request.GET.get("item_id")
        if not self.__validate_item_id(item_id):
            return HTTPResponse(500, "No such item with id '" + item_id + "' does not exist.")

        cart = request.session.cart

        # Find the item in the cart
        itemIndex = -1
        for i in range(len(cart.items)):
            if item_id == cart.items[i]:
                itemIndex = i
                break

        if itemIndex < 0:
            itemIndex = len(cart.items)
            cart.items.append(item_id)

        # Update the quantity of that item in the cart
        current_quantity = cart.item_quantities.get(item_id, 0)
        current_quantity += int(request.GET.get("quantity"))

        # Check to see if the cart is eligible for any special discounts
        special_discount_message = self.__check_cart_for_discounts(cart)

        # Send back the response
        response_body = Template("""
            <div class='addToCartConfirmation'>
                The item {{ item_name }} has been added to your cart.<br />
                There are {{ quantity }} of them in your cart.
            </div>
            <div class='specialDiscountMessage'>
                {{ special_discount_message }}
            </div>
        """).render({
            "item_name": request.GET["item_name"],
            "quantity": current_quantity,
            "special_discount_message": special_discount_message,
        })
        return HTTPResponse(200, response_body)

    def __check_cart_for_discounts(self, cart):
        """ Checks to see if the cart qualifies for any any of the item-pair
            discounts being offered (for example, if the cart contains
            a soccer ball and goalie gloves, the "goal keeper" discount
            would be applied).
            Returns a description of the discounts, or `""` if no
            discounts apply. """
        cxn = sqlite3.connect(self.settings.DATABASE_PATH)
        discounts = []
        for item0 in cart.items:
            for item1 in cart.items:
                result = cxn.execute("""
                    SELECT discount_name, discount_amount FROM item_discounts
                    WHERE item0 = %s and item1 = %s
                """ %(item0, item1))
                result = result.fetchone()
                if result == None:
                    continue
                discounts.append(result)
        cart.discounts = discounts

        discounts_str = ""
        total_discount = 0
        for name_amount in cart.discounts:
            name = name_amount[0]
            amount = name_amount[1]
            discounts_str += ", " + name
        discounts_str = discounts_str[2:]

        if total_discount > 0:
            return """
                This shopping cart is eligible for the following discounts: %s<br>
                For a total savings of $%s.
            """ %(discounts_str, total_discount)
        return ""

    def __validate_item_id(self, item_id):
        try:
            cxn = sqlite3.connect(self.settings.DATABASE_PATH)
            result = cxn.execute("SELECT * FROM items WHERE id = " + item_id)
            result = result.fetchone()
            cxn.close()
            if result == None:
                return False
            else:
                return True
        except:
            return False
