CREATE
(frontend:Service {name:'frontend'}),
(checkout:Service {name:'checkout'}),
(payment:Service {name:'payment'}),
(email:Service {name:'email'}),
(cart:Service {name:'cart'}),
(productCatalog:Service {name:'product-catalog'}),
(currency:Service {name:'currency'}),
(shipping:Service {name:'shipping'}),
(recommendation:Service {name:'recommendation'}),
(redis:Service {name:'redis'}),
(kafka:Service {name:'kafka'}),
(visaValidation:Service {name:'visa-validation'});

MATCH
(frontend:Service {name:'frontend'}),
(checkout:Service {name:'checkout'}),
(payment:Service {name:'payment'}),
(email:Service {name:'email'}),
(cart:Service {name:'cart'}),
(productCatalog:Service {name:'product-catalog'}),
(currency:Service {name:'currency'}),
(shipping:Service {name:'shipping'}),
(recommendation:Service {name:'recommendation'}),
(redis:Service {name:'redis'}),
(kafka:Service {name:'kafka'}),
(visaValidation:Service {name:'visa-validation'})

CREATE
(frontend)-[:CALLS]->(checkout),
(frontend)-[:CALLS]->(cart),
(frontend)-[:CALLS]->(productCatalog),
(checkout)-[:CALLS]->(payment),
(checkout)-[:CALLS]->(email),
(checkout)-[:CALLS]->(shipping),
(payment)-[:CALLS]->(visaValidation),
(cart)-[:CALLS]->(redis),
(productCatalog)-[:CALLS]->(redis),
(recommendation)-[:CALLS]->(productCatalog),
(shipping)-[:CALLS]->(currency),
(payment)-[:USES]->(redis),
(email)-[:USES]->(kafka);
