import { database } from "../../db.js";

// PostgreSQL returns NUMERIC values as strings
interface MonthlyEmissionsRow {
    month: string;
    scope_1_kg_co2e: string;
    scope_2_kg_co2e: string;
    total_kg_co2e: string;
}

export interface MonthlyEmissions {
    month: string;
    scope1KgCO2e: number;
    scope2KgCO2e: number;
    totalKgCO2e: number;
}

// calculate monthly Scope 1 and Scope 2 emissions from cleaned activity data
const monthlyEmissionsQuery = `
    -- calculate Scope 1 emissions from fuel deliveries
    WITH scope_1 AS (
        SELECT
            DATE_TRUNC('month', fuel.delivery_date)::date AS month,
            SUM(
                fuel.quantity_litres
                * factor.kg_co2e_per_unit
            ) AS kg_co2e
        FROM fuel_deliveries AS fuel
        JOIN emission_factors AS factor
            ON factor.activity = CASE fuel.fuel_type
                WHEN 'Diesel'
                    THEN 'Diesel combustion (stationary & transport)'
                WHEN 'Petrol (ULP)'
                    THEN 'Petrol (ULP) combustion'
                ELSE NULL
            END
            AND factor.scope = 1
            AND factor.unit = 'L'
        GROUP BY month
    ),
    -- calculate Scope 2 emissions from electricity readings
    scope_2 AS (
        SELECT
            DATE_TRUNC('month', electricity.period)::date AS month,
            SUM(
                electricity.consumption_kwh
                * factor.kg_co2e_per_unit
            ) AS kg_co2e
        FROM electricity_readings AS electricity
        JOIN emission_factors AS factor
            ON factor.activity = 'Grid electricity - Queensland'
            AND factor.scope = 2
            AND factor.unit = 'kWh'
        GROUP BY month
    ),
    -- include months that appear in either emissions scope
    months AS (
        SELECT month FROM scope_1

        UNION

        SELECT month FROM scope_2
    )
    SELECT
        TO_CHAR(months.month, 'YYYY-MM') AS month,
        ROUND(
            COALESCE(scope_1.kg_co2e, 0),
            2
        ) AS scope_1_kg_co2e,
        ROUND(
            COALESCE(scope_2.kg_co2e, 0),
            2
        ) AS scope_2_kg_co2e,
        ROUND(
            COALESCE(scope_1.kg_co2e, 0)
            + COALESCE(scope_2.kg_co2e, 0),
            2
        ) AS total_kg_co2e
    FROM months
    LEFT JOIN scope_1
        ON scope_1.month = months.month
    LEFT JOIN scope_2
        ON scope_2.month = months.month
    ORDER BY months.month
`;

export async function getMonthlyEmissions(): Promise<MonthlyEmissions[]> {
    const result =
        await database.query<MonthlyEmissionsRow>(
            monthlyEmissionsQuery
        );

    // convert database values to the API response format
    return result.rows.map((row) => ({
        month: row.month,
        scope1KgCO2e: Number(row.scope_1_kg_co2e),
        scope2KgCO2e: Number(row.scope_2_kg_co2e),
        totalKgCO2e: Number(row.total_kg_co2e)
    }));
}
