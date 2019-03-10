
#include "nvcategory_util.hpp"


#include <nvstrings/NVCategory.h>
#include <nvstrings/NVStrings.h>
#include "rmm/rmm.h"

#include "utilities/error_utils.hpp"
#include "utilities/nvtx/nvtx_utils.h"


gdf_error nvcategory_gather(gdf_column * column, NVCategory * nv_category){


  GDF_REQUIRE(nv_category != nullptr,GDF_INVALID_API_CALL );
  GDF_REQUIRE(column->dtype == GDF_STRING_CATEGORY,GDF_UNSUPPORTED_DTYPE);

  NVCategory * new_category = nv_category->gather(static_cast<nv_category_index_type *>(column->data),
                                                          column->size,
                                                          DEVICE_ALLOCATED);
  new_category->get_values(static_cast<nv_category_index_type *>(column->data),
                           DEVICE_ALLOCATED);

  //This is questionable behavior and should be reviewed by peers
  //Smart pointers would be lovely here
  if(column->dtype_info.category != nullptr){
    NVCategory::destroy(static_cast<NVCategory *>(column->dtype_info.category));
  }
  column->dtype_info.category = new_category;


  return GDF_SUCCESS;
}

gdf_error validate_categories(gdf_column * input_columns[], int num_columns, gdf_size_type & total_count){
  total_count = 0;
  for (int i = 0; i < num_columns; ++i) {
    gdf_column* current_column = input_columns[i];
    GDF_REQUIRE(current_column != nullptr,GDF_DATASET_EMPTY);
    GDF_REQUIRE(current_column->data != nullptr,GDF_DATASET_EMPTY);
    GDF_REQUIRE(current_column->dtype == GDF_STRING_CATEGORY,GDF_UNSUPPORTED_DTYPE);

    total_count += input_columns[i]->size;
  }
  return GDF_SUCCESS;
}

NVCategory * combine_column_categories(gdf_column * input_columns[],int num_columns){
  NVCategory * combined_category = static_cast<NVCategory *>(
        input_columns[0]->dtype_info.category)->copy();

    for(int column_index = 1; column_index < num_columns; column_index++){
      NVCategory * temp = combined_category;
      combined_category = combined_category->merge_and_remap(
          * static_cast<NVCategory *>(
              input_columns[column_index]->dtype_info.category));
      NVCategory::destroy(temp);
    }
    return combined_category;
}

gdf_error concat_categories(gdf_column * input_columns[],gdf_column * output_column, int num_columns){

  gdf_size_type total_count;
  gdf_error err = validate_categories(input_columns,num_columns,total_count);
  GDF_REQUIRE(err == GDF_SUCCESS,err);
  GDF_REQUIRE(total_count <= output_column->size,GDF_COLUMN_SIZE_MISMATCH);
  GDF_REQUIRE(output_column->dtype == GDF_STRING_CATEGORY,GDF_UNSUPPORTED_DTYPE);
  //TODO: we have no way to jsut copy a category this will fail if someone calls concat
  //on a single input
  GDF_REQUIRE(num_columns >= 1,GDF_DATASET_EMPTY);

  NVCategory * combined_category = combine_column_categories(input_columns,num_columns);
  combined_category->get_values(
        static_cast<nv_category_index_type *>(output_column->data),
        true);
  output_column->dtype_info.category = (void *) combined_category;



  return GDF_SUCCESS;
}


gdf_error sync_column_categories(gdf_column * input_columns[],gdf_column * output_columns[], int num_columns){

  GDF_REQUIRE(num_columns > 0,GDF_DATASET_EMPTY);
  gdf_size_type total_count;

  gdf_error err = validate_categories(input_columns,num_columns,total_count);
  GDF_REQUIRE(GDF_SUCCESS == err, err);

  err = validate_categories(output_columns,num_columns,total_count);
  GDF_REQUIRE(GDF_SUCCESS == err, err);

  for(int column_index = 0; column_index < num_columns; column_index++){
    GDF_REQUIRE(input_columns[column_index]->size == output_columns[column_index]->size,GDF_COLUMN_SIZE_MISMATCH);
  }

  NVCategory * combined_category = combine_column_categories(input_columns,num_columns);

  gdf_size_type current_column_start_position = 0;
  for(int column_index = 0; column_index < num_columns; column_index++){
    gdf_size_type column_size = output_columns[column_index]->size;
    gdf_size_type size_to_copy =  column_size * sizeof(nv_category_index_type);
    CUDA_TRY( cudaMemcpy(output_columns[column_index]->data,
                          combined_category->values_cptr() + current_column_start_position,
                         size_to_copy,
                          cudaMemcpyDeviceToDevice));

    //TODO: becuase of how gather works we are making a copy to preserve dictionaries as the same
    //this has an overhead of having to store more than is necessary. remove when gather preserving dictionary is available for nvcategory
    output_columns[column_index]->dtype_info.category = combined_category->copy();

    current_column_start_position += column_size;
  }

  NVCategory::destroy(combined_category);

  return GDF_SUCCESS;
}

gdf_error free_nvcategory(gdf_column * column){
  NVCategory::destroy(static_cast<NVCategory *>(column->dtype_info.category));
  column->dtype_info.category = nullptr;
  return GDF_SUCCESS;
}