/* global module */

module.exports = {
    "extends": "stylelint-config-standard-scss",

    "plugins": [
        "stylelint-order"
    ],

    "rules": {
        "order/order": [
            "custom-properties",
            "declarations"
        ],
        "property-no-vendor-prefix": null,
        "color-function-alias-notation": null,
        "color-function-notation": null,
        "declaration-block-no-redundant-longhand-properties": null,
        "no-descending-specificity": null,
        "alpha-value-notation": null,
        "media-feature-range-notation": null,
    },
    "overrides": [
        {
            "files": [ "../**/themes/reeltalk-*.scss" ],
            "rules": {
                "no-invalid-position-at-import-rule": null
            }
        }
    ]
};
