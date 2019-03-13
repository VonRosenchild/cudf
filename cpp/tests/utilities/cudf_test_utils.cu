/*
 * Copyright (c) 2018, NVIDIA CORPORATION.
 *
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

#include "cudf_test_utils.cuh"

#include <algorithm>

namespace {

namespace detail {

// When streaming char-like types, the standard library streams tend to treat
// them as characters rather than numbers, e.g. you would get an 'a' instead of 97.
// The following function(s) ensure we "promote" such values to integers before
// they're streamed

template <typename T>
const T& promote_for_streaming(const T& x) { return x; }


//int promote_for_streaming(const char& x)          { return x; }
//int promote_for_streaming(const unsigned char& x) { return x; }
int promote_for_streaming(const signed char& x)   { return x; }

} // namespace detail


struct column_printer {
    template<typename Element>
    void operator()(gdf_column const* the_column, unsigned min_printing_width)
    {
        gdf_size_type num_rows { the_column->size };

        Element const* column_data { static_cast<Element const*>(the_column->data) };

        std::vector<Element> host_side_data(num_rows);
        cudaMemcpy(host_side_data.data(), column_data, num_rows * sizeof(Element), cudaMemcpyDeviceToHost);


    std::vector<gdf_valid_type> h_mask(gdf_valid_allocation_size(num_rows), ~gdf_valid_type{0});
    if (nullptr != the_column->valid) {
      cudaMemcpy(h_mask.data(), the_column->valid,
                 gdf_num_bitmask_elements(num_rows) * sizeof(gdf_valid_type), cudaMemcpyDeviceToHost);
    }

        for (gdf_size_type i = 0; i < num_rows; ++i) {
            std::cout << std::setw(min_printing_width);
            if (gdf_is_valid(h_mask.data(), i)) {
                std::cout << detail::promote_for_streaming(host_side_data[i]);
            }
            else {
                std::cout << null_representative;
            }
            std::cout << ' ';
        }
        std::cout << std::endl;
    }
};

} // namespace

void print_gdf_column(gdf_column const * the_column, unsigned min_printing_width)
{
    cudf::type_dispatcher(the_column->dtype, column_printer{}, the_column, min_printing_width);
}

void print_valid_data(const gdf_valid_type *validity_mask, 
                      const size_t num_rows)
{
  cudaError_t error;
  cudaPointerAttributes attrib;
  cudaPointerGetAttributes(&attrib, validity_mask);
  error = cudaGetLastError();

  std::vector<gdf_valid_type> h_mask(gdf_valid_allocation_size(num_rows));
  if (error != cudaErrorInvalidValue && attrib.memoryType == cudaMemoryTypeDevice)
    cudaMemcpy(h_mask.data(), validity_mask, gdf_valid_allocation_size(num_rows), cudaMemcpyDeviceToHost);
  else
    memcpy(h_mask.data(), validity_mask, gdf_valid_allocation_size(num_rows));

  std::transform(
      h_mask.begin(), h_mask.begin() + gdf_num_bitmask_elements(num_rows),
      std::ostream_iterator<std::string>(std::cout, " "), [](gdf_valid_type x) {
        auto bits = std::bitset<GDF_VALID_BITSIZE>(x).to_string('@');
        return std::string(bits.rbegin(), bits.rend());
      });
  std::cout << std::endl;
}

