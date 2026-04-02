RYANAIR = {
    "cookie_accept": '[data-ref="cookie.accept-all"]',
    "destination_card": "button[data-iata-code]",
    "city_name": ".result-card-content__destination",
    "dates": ".result-card-content__dates",
    "duration": ".result-card-content__duration--padding",
    "price": ".result-card-content__price--value",
}

WIZZAIR = {
    "cookie_accept": "#accept",
    "return_trip_toggle": '[data-test="universal-flight-way-selector"] input[value="return"]',
    "oneway_trip_toggle": '[data-test="universal-flight-way-selector"] input[value="oneway"]',
    "origin_input": '[data-test="search-departure-station"]',
    "origin_dropdown_item": 'label[data-test="{IATA_CODE}"]',
    "destination_input": '[data-test="search-arrival-station"]',
    "departure_date_input": '[data-test="universal-search-dropdown"]',
    "departure_date_clickable": '[data-test="universal-search-dropdown"] .universal-search-dropdown.w-input',
    "departure_date_display": '[data-test="universal-search-dates-departure"]',
    "search_button": '[data-test="fare-finder-smart-search-submit"]',
    "destination_card": '[data-test^="fare-accordion--"]',
    "destination_card_header": '[data-test^="fare-accordion-header--"]',
    "city_name": 'p[data-test]',
    "dates": '[data-test="offer-month"]',
    # price extracted from data-test attr, e.g. "amount-39.98-currency-EUR"
    "price": '[data-test^="amount-"]',
    "price_container": '.price-header-offer__price-container--amount',
    "duration": '[data-test="offer-trip-duration"]',
    "booking_link": '[data-test="fare-finder-checkout"]',
    "card_expand_arrow": '[data-test^="fare-accordion-arrow--"]',
    "card_body": '[data-test^="fare-accordion-body--"]',
    "calendar_day_outbound": '[data-test^="fare-finder-day-selector-day-outbound-"]',
    "calendar_day_return": '[data-test^="fare-finder-day-selector-day-return-"]',
}

HOSTELWORLD = {
    "cookie_accept": "#truste-consent-button",
    "hostel_card": "a.property-card-container.horizontal",
    "hostel_name": "a.property-card-container.horizontal .property-name span",
    # Cards can show two prices: [0]=Privates, [1]=Dorms
    "price_per_night": "a.property-card-container.horizontal strong.current",
    "rating": "a.property-card-container.horizontal .score",
    "review_count": "a.property-card-container.horizontal .num-reviews",
    # Card itself is the <a> tag — read href directly
    "booking_link": "a.property-card-container.horizontal",
    "sort_button": "button.sort-mobile",
    "sort_by_price": ".select-list li[role='option'] button.item-content",
    "filter_dorm": ".room-type-container:first-child .checkbox-input",
    "filter_private": ".room-type-container:last-child .checkbox-input",
    "filters_button": ".filters button.pwa-pill-button",
    "pagination_wrapper": ".pagination-wrapper",
    "next_page_button": "button.page-nav.nav-right",
    "page_number_button": "button.page-number",
}

#these may break on updates - I should implement proper CICD for this
PRICE_SR_TEXT = '[data-testid="availability-rate-information"] .bc946a29db'
PRICE_LABEL = '[data-testid="price-for-x-nights"]'
PRICE_TAXES = '[data-testid="taxes-and-charges"]'
SCORE_NUMBER = '[data-testid="review-score"] div.f63b14ab7a.dff2e52086'
SCORE_LABEL = '[data-testid="review-score"] div.f63b14ab7a.f546354b44'
CTA_LINK = '[data-testid="availability-cta-btn"]'
RESULTS_LIST = '[data-results-container="1"]'
