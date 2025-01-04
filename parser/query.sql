SELECT *
FROM transactions
WHERE amount < 0.5
ORDER BY sub_id ASC