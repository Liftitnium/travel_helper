"""
=============================================================
HOW TO FILL IN THESE SELECTORS:
=============================================================
1. Open the website in Chrome
2. Right-click the element you need -> click "Inspect"
3. In DevTools, right-click the highlighted HTML -> Copy -> Copy selector
4. Paste it below, replacing ___REPLACE_WITH_ACTUAL_SELECTOR___
=============================================================
"""

RYANAIR = {
    "cookie_accept": '[data-ref="cookie.accept-all"]',

    # Each destination card is a <button> with data-iata-code and data-ref attributes.
    # data-iata-code = "ESU", data-ref = "RESULT_ESU_2026-04-10_2026-04-17"
    "destination_card": "button[data-iata-code]",

    # Child elements inside each card button
    "city_name": ".result-card-content__destination",
    "dates": ".result-card-content__dates",
    "duration": ".result-card-content__duration--padding",
    "price": ".result-card-content__price--value",
}

WIZZAIR = {
    # ── FORM ELEMENTS ──────────────────────────────────────────────────────────

    # Cookie consent "Accept all" button (only appears on the first visit / fresh session)
    "cookie_accept": "#accept",

    # Return/One-way radio toggle.
    # The IDs (radio-button-id-4 / -5) are dynamically generated — don't use them.
    # Use the value attribute, scoped to the fieldset that holds the selector.
    "return_trip_toggle": '[data-test="universal-flight-way-selector"] input[value="return"]',
    "oneway_trip_toggle": '[data-test="universal-flight-way-selector"] input[value="oneway"]',

    # "Leaving from" autocomplete input
    "origin_input": '[data-test="search-departure-station"]',

    # Airport dropdown item after typing (already known — confirmed still valid)
    "origin_dropdown_item": 'label[data-test="{IATA_CODE}"]',

    # "Destination" autocomplete input
    "destination_input": '[data-test="search-arrival-station"]',

    # Date picker — NOT a real <input>; it's a clickable <div>.
    # Click this to open the date/flexible-travel picker modal.
    "departure_date_input": '[data-test="universal-search-dropdown"]',

    # The inner focusable div (tabindex="0") you can send keys/clicks to:
    "departure_date_clickable": '[data-test="universal-search-dropdown"] .universal-search-dropdown.w-input',

    # Current date display text (read-only span showing selected date or "Anytime for 1 week")
    "departure_date_display": '[data-test="universal-search-dates-departure"]',

    # Search / submit button
    "search_button": '[data-test="fare-finder-smart-search-submit"]',

    # ── RESULT ELEMENTS ────────────────────────────────────────────────────────

    # Each destination result card — <li data-test="fare-accordion--0">, --1, --2 …
    "destination_card": '[data-test^="fare-accordion--"]',

    # Clickable header row of each card (triggers calendar expansion)
    "destination_card_header": '[data-test^="fare-accordion-header--"]',

    # City / airport name inside each card.
    # Wizz Air sets data-test to the IATA code of the destination (e.g. "MXP", "LTN").
    # Scoped within a card: [data-test^="fare-accordion--"] p[data-test]
    "city_name": 'p[data-test]',  # use within card scope

    # Date range shown on the card ("in October", "in April - May", etc.)
    "dates": '[data-test="offer-month"]',

    # Price amount span.
    # data-test is dynamic: "amount-39.98-currency-EUR" — price changes per route.
    # Reliable approach: scope to card and use attribute-starts-with selector.
    "price": '[data-test^="amount-"]',  # use within card scope

    # Price container div (stable class, wraps the amount span):
    "price_container": '.price-header-offer__price-container--amount',

    # Flight duration ("2h 15m", "3h 25m", etc.)
    "duration": '[data-test="offer-trip-duration"]',

    # "Start booking" CTA button — only appears AFTER expanding a card
    # (click the header or arrow) AND selecting a specific outbound date.
    "booking_link": '[data-test="fare-finder-checkout"]',

    # Expand/collapse arrow button on each card (to open the date calendar):
    "card_expand_arrow": '[data-test^="fare-accordion-arrow--"]',

    # Expanded calendar body (contains individual day cells):
    "card_body": '[data-test^="fare-accordion-body--"]',

    # Individual day cells in the outbound calendar:
    "calendar_day_outbound": '[data-test^="fare-finder-day-selector-day-outbound-"]',

    # Individual day cells in the return calendar:
    "calendar_day_return": '[data-test^="fare-finder-day-selector-day-return-"]',
}

HOSTELWORLD = {
    # ── Cookie consent ─────────────────────────────────────────────────────────
    # TrustArc "Bottom Bar" (noticeType=bb, behavior=implied).
    # The div #consent_blackbar is injected by TrustArc and the Accept button
    # carries the standard TrustArc ID. Only visible on a first / cookie-cleared visit.
    "cookie_accept": "#truste-consent-button",

    # ── Hostel card ─────────────────────────────────────────────────────────────
    # Every result in the "All properties" list is an <a> element with these two
    # classes. The "featured" mini-cards at the top use "property-card-container"
    # WITHOUT "horizontal", so this selector is already scoped to the main list.
    "hostel_card": "a.property-card-container.horizontal",

    # ── Hostel name ─────────────────────────────────────────────────────────────
    # Inside each card, the .property-name div wraps a bare <span> with the text.
    "hostel_name": "a.property-card-container.horizontal .property-name span",

    # ── Price per night ─────────────────────────────────────────────────────────
    # Every card can show TWO prices (Privates From + Dorms From).
    # Both use <strong class="current">€XX</strong>.
    # Use [0] for the first shown price (usually Privates) and [1] for Dorms,
    # OR use the more targeted selectors below.
    "price_per_night": "a.property-card-container.horizontal strong.current",

    # Targeted dorm-only price (scrape .accommodation-label sibling to confirm "Dorms From"):
    # "dorm_price": "a.property-card-container.horizontal .property-accommodation-price strong.current"
    # (first .property-accommodation-price whose text starts with "Dorms From" → strong.current)
    # NOTE: prices ARE per night (the right-sidebar filter is labelled "Average price per night").

    # ── Rating ──────────────────────────────────────────────────────────────────
    # A plain <span class="score"> inside the .rating element.
    # Values like "9.2", "10" — rating is OUT OF 10.
    "rating": "a.property-card-container.horizontal .score",

    # ── Review count ────────────────────────────────────────────────────────────
    # Rendered as "(3111)" — the parentheses are part of the text content.
    # Strip them with .strip("()").replace(",","") if you need an integer.
    "review_count": "a.property-card-container.horizontal .num-reviews",

    # ── Booking link ────────────────────────────────────────────────────────────
    # The card itself IS the <a> tag; there are no nested <a> elements inside.
    # Read card.get_attribute("href") directly.
    # href format: /pwa/hosteldetails.php/<Slug>/<City>/<ID>?from=…&to=…&guests=…
    "booking_link": "a.property-card-container.horizontal",

    # ═══════════════════ BONUS ══════════════════════════════════════════════════

    # ── Sort by price ───────────────────────────────────────────────────────────
    # Step 1: click the Sort button to open the dropdown.
    # On desktop the trigger lives inside .sort-desktop; on mobile it's the button below.
    "sort_button": "button.sort-mobile",          # click this first
    # Step 2: after the dropdown opens, click "Lowest price":
    "sort_by_price": ".select-list li[role='option'] button.item-content",
    # To target "Lowest price" specifically by text (Playwright/Selenium):
    #   driver.find_element(By.XPATH, "//button[contains(@class,'item-content') and text()='Lowest price']")

    # ── Dorm / Private room-type filter ─────────────────────────────────────────
    # Lives inside the Filters modal (click button.pwa-pill-button → text "Filters" first).
    # The modal splits room types into two columns: "Dorm" (left) and "Private Room" (right).
    # Each checkbox is <input class="checkbox-input"> inside a <label class="checkbox-wrapper">.
    # There are NO unique IDs or data-testids on these checkboxes.
    #
    # Selector for the DORM section's first checkbox (Ensuite Room):
    "filter_dorm": ".room-type-container:first-child .checkbox-input",
    # For "Mixed Dorm" specifically, use XPath or filter by sibling label text:
    #   .room-type-container:first-child .checkbox-item:nth-child(2) .checkbox-input
    #
    # Selector for the PRIVATE ROOM section's first checkbox:
    "filter_private": ".room-type-container:last-child .checkbox-input",
    # The Filters button itself:
    "filters_button": ".filters button.pwa-pill-button",

    # ── Pagination ──────────────────────────────────────────────────────────────
    # Results use NUMBERED PAGINATION (not infinite scroll).
    # Porto shows 55 properties across 2 pages (~30 per page).
    "pagination_wrapper": ".pagination-wrapper",
    "next_page_button":   "button.page-nav.nav-right",    # aria-label="arrow-right"
    "page_number_button": "button.page-number",            # e.g. "1", "2"
}

# Original (crossed-out) price — only present when a discount is active
# e.g. "€ 88" when current price is "€ 47"
# NOTE: Booking.com uses obfuscated class names (e.g. fff1944c52 d68334ea31 ab607752a2).
# More reliable: parse the screen-reader text inside [data-testid="availability-rate-information"]
# which always reads: "Original price € XX. Current price € YY."
PRICE_SR_TEXT  = '[data-testid="availability-rate-information"] .bc946a29db'  # ⚠ may change

# "2 nights, 1 adult" label (confirms price is TOTAL STAY, not per night)
PRICE_LABEL    = '[data-testid="price-for-x-nights"]'

# "Includes taxes and fees" note
PRICE_TAXES    = '[data-testid="taxes-and-charges"]'

# Numeric score only (e.g. "8.8"), scraped out of review-score
SCORE_NUMBER   = '[data-testid="review-score"] div.f63b14ab7a.dff2e52086'  # ⚠ obfuscated class

# Verbal label only ("Excellent", "Very Good", etc.)
SCORE_LABEL    = '[data-testid="review-score"] div.f63b14ab7a.f546354b44'  # ⚠ obfuscated class

# "See availability" CTA link (same href as title-link, opens in _blank)
CTA_LINK       = '[data-testid="availability-cta-btn"]'

# Results parent container (use for iteration)
RESULTS_LIST   = '[data-results-container="1"]'
