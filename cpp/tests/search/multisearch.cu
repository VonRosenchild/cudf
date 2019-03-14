/*
 * Copyright 2019 BlazingDB, Inc.
 *     Copyright 2019 Eyal Rozenberg <eyalroz@blazingdb.com>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <tests/utilities/cudf_test_fixtures.h> // for GdfTest
#include <tests/utilities/cudf_test_utils.cuh>
#include <tests/utilities/column_wrapper.cuh>

#include <cudf.h>

#include <utilities/miscellany.hpp>

#include <gtest/gtest.h>

#include <iostream>
//#include <tuple>
#include <random>

enum : bool {
    find_first_greater = true,
    find_first_greater_or_equal = false
};

enum : bool {
    nulls_appear_before_values = true,
    nulls_appear_after_values = false
};

enum : bool {
    use_haystack_length_for_not_found = true,
    use_null_for_not_found = false
};


template <typename T>
using column_wrapper = cudf::test::column_wrapper<int>;

enum : bool {
    non_nullable = false,
    nullable = true
};

// TODO: Make this templated on a tuple type, and use the gadget above to be able to work with the parameter packs directly.
struct Multisearch : public GdfTest {
    std::default_random_engine randomness_generator;
    std::uniform_int_distribution<gdf_size_type> column_size_distribution{1000, 10000};
    gdf_size_type random_column_size() { return column_size_distribution(randomness_generator); }

    Multisearch() = default;
    ~Multisearch() = default;
};

/*typedef ::testing::Types<
    int8_t,
    int16_t,
    int32_t,
    int64_t,
    float,
    double,
    gdf_date32,
    gdf_date64,
    gdf_timestamp
    // Nothing for categories - they're not inherently ordred
    // Nothing strings
  > Implementations;

TYPED_TEST_CASE(Multisearch, Implementations);

*/

TEST(Multisearch, fails_when_no_haystack_columns_provided)
{
    gdf_size_type num_columns { 0 };
    gdf_column results;
    gdf_column single_haystack_column;
    gdf_column* haystack_columns[] = { & single_haystack_column };
    gdf_column single_needle_column;
    gdf_column* needle_columns[] = { & single_needle_column };


    auto result = gdf_multisearch(
        &results,
        &(haystack_columns[0]),
        &(needle_columns[0]),
        num_columns,
        find_first_greater,
        nulls_appear_before_values,
        use_haystack_length_for_not_found);

    ASSERT_NE(result, GDF_SUCCESS);
}

TEST(Multisearch, succeeds_with_single_non_null_column_one_needle)
{
    using single_element_type = int;

    gdf_column_index_type num_columns     { 1 };

    // single_element_type uniform_value { 123 };
    std::vector<single_element_type> haystack_data { 10, 20, 30, 40, 50 };
    std::vector<single_element_type> needle_data { 20 };
    std::vector<gdf_size_type> dummy_result_data { 1234567 };

    auto single_haystack_column = cudf::test::column_wrapper<single_element_type>(haystack_data);
    auto single_needle_column   = cudf::test::column_wrapper<single_element_type>(needle_data);
//  auto results                = cudf::test::column_wrapper<gdf_size_type      >(num_needles,     non_nullable);
    auto results                = cudf::test::column_wrapper<gdf_size_type>(dummy_result_data);

//    single_haystack_column.print();
//    single_needle_column.print();
//    results.print();

    gdf_column* haystack_columns[] = { single_haystack_column.get() };
    gdf_column* needle_columns[]   = { single_needle_column.get()   };

    gdf_error result;
    ASSERT_NO_THROW(
        result = gdf_multisearch(
            results.get(),
            &(haystack_columns[0]),
            &(needle_columns[0]),
            num_columns,
            find_first_greater,
            nulls_appear_before_values,
            use_haystack_length_for_not_found);
    );
    ASSERT_EQ(result, GDF_SUCCESS);
    auto results_on_host = results.to_host();
    ASSERT_EQ(results.get()->valid, nullptr); // Just a sanity check really
    ASSERT_EQ(std::get<0>(results_on_host).size(), size_t{1});
    if (not std::get<0>(results_on_host).empty()) {
        ASSERT_EQ(std::get<0>(results_on_host)[0], 2); // at position 2 we have 30, greater than 20.
    }
}
