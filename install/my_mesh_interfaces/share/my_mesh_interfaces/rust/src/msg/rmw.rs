#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};


#[link(name = "my_mesh_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__my_mesh_interfaces__msg__MeshScan() -> *const std::ffi::c_void;
}

#[link(name = "my_mesh_interfaces__rosidl_generator_c")]
extern "C" {
    fn my_mesh_interfaces__msg__MeshScan__init(msg: *mut MeshScan) -> bool;
    fn my_mesh_interfaces__msg__MeshScan__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MeshScan>, size: usize) -> bool;
    fn my_mesh_interfaces__msg__MeshScan__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MeshScan>);
    fn my_mesh_interfaces__msg__MeshScan__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MeshScan>, out_seq: *mut rosidl_runtime_rs::Sequence<MeshScan>) -> bool;
}

// Corresponds to my_mesh_interfaces__msg__MeshScan
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MeshScan {

    // This member is not documented.
    #[allow(missing_docs)]
    pub session_id: u64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub sequence_id: u64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub map_data: nav_msgs::msg::rmw::OccupancyGrid,


    // This member is not documented.
    #[allow(missing_docs)]
    pub transmission_stamp: builtin_interfaces::msg::rmw::Time,

}



impl Default for MeshScan {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !my_mesh_interfaces__msg__MeshScan__init(&mut msg as *mut _) {
        panic!("Call to my_mesh_interfaces__msg__MeshScan__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MeshScan {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshScan__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshScan__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshScan__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MeshScan {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MeshScan where Self: Sized {
  const TYPE_NAME: &'static str = "my_mesh_interfaces/msg/MeshScan";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__my_mesh_interfaces__msg__MeshScan() }
  }
}


#[link(name = "my_mesh_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__my_mesh_interfaces__msg__MeshMap() -> *const std::ffi::c_void;
}

#[link(name = "my_mesh_interfaces__rosidl_generator_c")]
extern "C" {
    fn my_mesh_interfaces__msg__MeshMap__init(msg: *mut MeshMap) -> bool;
    fn my_mesh_interfaces__msg__MeshMap__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MeshMap>, size: usize) -> bool;
    fn my_mesh_interfaces__msg__MeshMap__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MeshMap>);
    fn my_mesh_interfaces__msg__MeshMap__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MeshMap>, out_seq: *mut rosidl_runtime_rs::Sequence<MeshMap>) -> bool;
}

// Corresponds to my_mesh_interfaces__msg__MeshMap
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MeshMap {

    // This member is not documented.
    #[allow(missing_docs)]
    pub session_id: u64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub sequence_id: u64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub transmission_stamp: builtin_interfaces::msg::rmw::Time,


    // This member is not documented.
    #[allow(missing_docs)]
    pub map_data: nav_msgs::msg::rmw::OccupancyGrid,

}



impl Default for MeshMap {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !my_mesh_interfaces__msg__MeshMap__init(&mut msg as *mut _) {
        panic!("Call to my_mesh_interfaces__msg__MeshMap__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MeshMap {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshMap__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshMap__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshMap__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MeshMap {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MeshMap where Self: Sized {
  const TYPE_NAME: &'static str = "my_mesh_interfaces/msg/MeshMap";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__my_mesh_interfaces__msg__MeshMap() }
  }
}


#[link(name = "my_mesh_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__my_mesh_interfaces__msg__MeshTf() -> *const std::ffi::c_void;
}

#[link(name = "my_mesh_interfaces__rosidl_generator_c")]
extern "C" {
    fn my_mesh_interfaces__msg__MeshTf__init(msg: *mut MeshTf) -> bool;
    fn my_mesh_interfaces__msg__MeshTf__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<MeshTf>, size: usize) -> bool;
    fn my_mesh_interfaces__msg__MeshTf__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<MeshTf>);
    fn my_mesh_interfaces__msg__MeshTf__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<MeshTf>, out_seq: *mut rosidl_runtime_rs::Sequence<MeshTf>) -> bool;
}

// Corresponds to my_mesh_interfaces__msg__MeshTf
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct MeshTf {

    // This member is not documented.
    #[allow(missing_docs)]
    pub session_id: u64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub sequence_id: u64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub transmission_stamp: builtin_interfaces::msg::rmw::Time,


    // This member is not documented.
    #[allow(missing_docs)]
    pub tf_data: tf2_msgs::msg::rmw::TFMessage,


    // This member is not documented.
    #[allow(missing_docs)]
    pub map_in_flight: bool,

}



impl Default for MeshTf {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !my_mesh_interfaces__msg__MeshTf__init(&mut msg as *mut _) {
        panic!("Call to my_mesh_interfaces__msg__MeshTf__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for MeshTf {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshTf__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshTf__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__MeshTf__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for MeshTf {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for MeshTf where Self: Sized {
  const TYPE_NAME: &'static str = "my_mesh_interfaces/msg/MeshTf";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__my_mesh_interfaces__msg__MeshTf() }
  }
}


#[link(name = "my_mesh_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_message_type_support_handle__my_mesh_interfaces__msg__SenderStatus() -> *const std::ffi::c_void;
}

#[link(name = "my_mesh_interfaces__rosidl_generator_c")]
extern "C" {
    fn my_mesh_interfaces__msg__SenderStatus__init(msg: *mut SenderStatus) -> bool;
    fn my_mesh_interfaces__msg__SenderStatus__Sequence__init(seq: *mut rosidl_runtime_rs::Sequence<SenderStatus>, size: usize) -> bool;
    fn my_mesh_interfaces__msg__SenderStatus__Sequence__fini(seq: *mut rosidl_runtime_rs::Sequence<SenderStatus>);
    fn my_mesh_interfaces__msg__SenderStatus__Sequence__copy(in_seq: &rosidl_runtime_rs::Sequence<SenderStatus>, out_seq: *mut rosidl_runtime_rs::Sequence<SenderStatus>) -> bool;
}

// Corresponds to my_mesh_interfaces__msg__SenderStatus
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]


// This struct is not documented.
#[allow(missing_docs)]

#[repr(C)]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct SenderStatus {

    // This member is not documented.
    #[allow(missing_docs)]
    pub session_id: u64,


    // This member is not documented.
    #[allow(missing_docs)]
    pub last_sequence_sent: u64,

}



impl Default for SenderStatus {
  fn default() -> Self {
    unsafe {
      let mut msg = std::mem::zeroed();
      if !my_mesh_interfaces__msg__SenderStatus__init(&mut msg as *mut _) {
        panic!("Call to my_mesh_interfaces__msg__SenderStatus__init() failed");
      }
      msg
    }
  }
}

impl rosidl_runtime_rs::SequenceAlloc for SenderStatus {
  fn sequence_init(seq: &mut rosidl_runtime_rs::Sequence<Self>, size: usize) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__SenderStatus__Sequence__init(seq as *mut _, size) }
  }
  fn sequence_fini(seq: &mut rosidl_runtime_rs::Sequence<Self>) {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__SenderStatus__Sequence__fini(seq as *mut _) }
  }
  fn sequence_copy(in_seq: &rosidl_runtime_rs::Sequence<Self>, out_seq: &mut rosidl_runtime_rs::Sequence<Self>) -> bool {
    // SAFETY: This is safe since the pointer is guaranteed to be valid/initialized.
    unsafe { my_mesh_interfaces__msg__SenderStatus__Sequence__copy(in_seq, out_seq as *mut _) }
  }
}

impl rosidl_runtime_rs::Message for SenderStatus {
  type RmwMsg = Self;
  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> { msg_cow }
  fn from_rmw_message(msg: Self::RmwMsg) -> Self { msg }
}

impl rosidl_runtime_rs::RmwMessage for SenderStatus where Self: Sized {
  const TYPE_NAME: &'static str = "my_mesh_interfaces/msg/SenderStatus";
  fn get_type_support() -> *const std::ffi::c_void {
    // SAFETY: No preconditions for this function.
    unsafe { rosidl_typesupport_c__get_message_type_support_handle__my_mesh_interfaces__msg__SenderStatus() }
  }
}


