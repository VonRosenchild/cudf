
/*
 * Copyright 2018 BlazingDB, Inc.
 *     Copyright 2018 Alexander Ocsa <alexander@blazingdb.com>
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
#pragma once

#include <climits>
#include <cstdint>

#include <utilities/cudf_utils.h>
#include <utilities/miscellany.hpp>
#include <stdint.h>
#include <string>

#ifndef CUDA_HOST_DEVICE_CALLABLE
#ifdef __CUDACC__
#define CUDA_HOST_DEVICE_CALLABLE __host__ __device__ inline
#define CUDA_DEVICE_CALLABLE __device__ inline
#define CUDA_LAUNCHABLE __global__
#else
#define CUDA_HOST_DEVICE_CALLABLE inline
#define CUDA_DEVICE_CALLABLE inline
#define CUDA_LAUNCHABLE
#endif
#endif

namespace gdf {
namespace util {


static constexpr int ValidSize = 32;
using ValidType = uint32_t;

template <typename T>
constexpr inline std::size_t size_in_bits() { return sizeof(T) * CHAR_BIT; }

// Instead of this function, use gdf_valid_allocation_size from legacy_bitmask.hpp
//CUDA_HOST_DEVICE_CALLABLE
//  size_t
//  valid_size(size_t column_length)
//{
//  const size_t n_ints = (column_length / ValidSize) + ((column_length % ValidSize) ? 1 : 0);
//  return n_ints * sizeof(ValidType);
//}


namespace detail {

template <typename BitContainer, typename Size>
constexpr CUDA_HOST_DEVICE_CALLABLE
Size intra_container_index(Size bit_index) { return bit_index % size_in_bits<BitContainer>(); }

template <typename BitContainer, typename Size>
constexpr CUDA_HOST_DEVICE_CALLABLE
Size bit_container_index(Size bit_index) { return bit_index / size_in_bits<BitContainer>(); }


} // namespace detail


template <typename BitContainer, typename Size>
constexpr CUDA_HOST_DEVICE_CALLABLE
void turn_bit_on(BitContainer* bits, Size bit_index)
{
    auto container_index = detail::bit_container_index<BitContainer, Size>(bit_index);
    auto intra_container_index = detail::intra_container_index<BitContainer, Size>(bit_index);
    bits[container_index] |= (BitContainer{1} << intra_container_index);
}

template <typename BitContainer, typename Size>
constexpr CUDA_HOST_DEVICE_CALLABLE
void turn_bit_off(BitContainer* bits, Size bit_index)
{
    auto container_index = detail::bit_container_index<BitContainer, Size>(bit_index);
    auto intra_container_index = detail::intra_container_index<BitContainer, Size>(bit_index);
    bits[container_index] &= ~((BitContainer{1} << intra_container_index));
}

CUDA_HOST_DEVICE_CALLABLE size_t last_byte_index(size_t column_size)
{
  return (column_size + 8 - 1) / 8;
}

/**
 * Checks if a bit is set within a bit-container, in which the bits
 * are ordered LSB to MSB
 *
 * @param bits[in] a bit container
 * @param bit_index[in] index within the sequence of bits in the container
 * @return true iff the bit is set
 */
template <typename BitContainer, typename Size>
constexpr CUDA_HOST_DEVICE_CALLABLE bool bit_is_set(const BitContainer& bit_container, Size bit_index)
{
    auto intra_container_index = detail::intra_container_index<BitContainer, Size>(bit_index);
    return bit_container & (BitContainer{1} << intra_container_index);
}

/**
 * Checks if a bit is set in a sequence of bits in container types,
 * such that within each container the bits are ordered LSB to MSB
 *
 * @param bits[in] pointer to the beginning of the sequence of bits
 * @param bit_index[in] index to bit check in the sequence
 * @return true iff the bit is set
 */
template <typename BitContainer, typename Size>
constexpr CUDA_HOST_DEVICE_CALLABLE bool bit_is_set(const BitContainer* bits, Size bit_index)
{
    auto container_index = detail::bit_container_index<BitContainer, Size>(bit_index);
    return bit_is_set<BitContainer, Size>(bits[container_index], bit_index);
}

template <typename BitContainer, typename Size>
inline gdf_size_type packed_bit_sequence_size_in_bytes (Size num_bits) {
    return cudf::util::div_rounding_up_safe<Size>(num_bits, size_in_bits<BitContainer>());
}


static inline std::string chartobin(gdf_valid_type c, size_t size = 8)
{
  std::string bin;
  bin.resize(size);
  bin[0] = 0;
  size_t i;
  for (i = 0; i < size; i++) {
    bin[i] = (c % 2) + '0';
    c /= 2;
  }
  return bin;
}

static inline std::string gdf_valid_to_str(const gdf_valid_type* valid, size_t column_size)
{
  size_t last_byte = gdf::util::last_byte_index(column_size);
  std::string response;
  for (size_t i = 0; i < last_byte; i++) {
    size_t n_bits = last_byte != i + 1 ? 8 : column_size - 8 * (last_byte - 1);
    auto result = chartobin(valid[i], n_bits);
    response += std::string(result);
  }
  return response;
}

} // namespace util
} // namespace gdf
