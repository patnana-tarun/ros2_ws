#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



// Corresponds to my_mesh_interfaces__msg__MeshScan

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
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
    pub map_data: nav_msgs::msg::OccupancyGrid,


    // This member is not documented.
    #[allow(missing_docs)]
    pub transmission_stamp: builtin_interfaces::msg::Time,

}



impl Default for MeshScan {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::MeshScan::default())
  }
}

impl rosidl_runtime_rs::Message for MeshScan {
  type RmwMsg = super::msg::rmw::MeshScan;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        session_id: msg.session_id,
        sequence_id: msg.sequence_id,
        map_data: nav_msgs::msg::OccupancyGrid::into_rmw_message(std::borrow::Cow::Owned(msg.map_data)).into_owned(),
        transmission_stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Owned(msg.transmission_stamp)).into_owned(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      session_id: msg.session_id,
      sequence_id: msg.sequence_id,
        map_data: nav_msgs::msg::OccupancyGrid::into_rmw_message(std::borrow::Cow::Borrowed(&msg.map_data)).into_owned(),
        transmission_stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Borrowed(&msg.transmission_stamp)).into_owned(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      session_id: msg.session_id,
      sequence_id: msg.sequence_id,
      map_data: nav_msgs::msg::OccupancyGrid::from_rmw_message(msg.map_data),
      transmission_stamp: builtin_interfaces::msg::Time::from_rmw_message(msg.transmission_stamp),
    }
  }
}


// Corresponds to my_mesh_interfaces__msg__MeshMap

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
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
    pub transmission_stamp: builtin_interfaces::msg::Time,


    // This member is not documented.
    #[allow(missing_docs)]
    pub map_data: nav_msgs::msg::OccupancyGrid,

}



impl Default for MeshMap {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::MeshMap::default())
  }
}

impl rosidl_runtime_rs::Message for MeshMap {
  type RmwMsg = super::msg::rmw::MeshMap;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        session_id: msg.session_id,
        sequence_id: msg.sequence_id,
        transmission_stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Owned(msg.transmission_stamp)).into_owned(),
        map_data: nav_msgs::msg::OccupancyGrid::into_rmw_message(std::borrow::Cow::Owned(msg.map_data)).into_owned(),
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      session_id: msg.session_id,
      sequence_id: msg.sequence_id,
        transmission_stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Borrowed(&msg.transmission_stamp)).into_owned(),
        map_data: nav_msgs::msg::OccupancyGrid::into_rmw_message(std::borrow::Cow::Borrowed(&msg.map_data)).into_owned(),
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      session_id: msg.session_id,
      sequence_id: msg.sequence_id,
      transmission_stamp: builtin_interfaces::msg::Time::from_rmw_message(msg.transmission_stamp),
      map_data: nav_msgs::msg::OccupancyGrid::from_rmw_message(msg.map_data),
    }
  }
}


// Corresponds to my_mesh_interfaces__msg__MeshTf

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
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
    pub transmission_stamp: builtin_interfaces::msg::Time,


    // This member is not documented.
    #[allow(missing_docs)]
    pub tf_data: tf2_msgs::msg::TFMessage,


    // This member is not documented.
    #[allow(missing_docs)]
    pub map_in_flight: bool,

}



impl Default for MeshTf {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::MeshTf::default())
  }
}

impl rosidl_runtime_rs::Message for MeshTf {
  type RmwMsg = super::msg::rmw::MeshTf;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        session_id: msg.session_id,
        sequence_id: msg.sequence_id,
        transmission_stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Owned(msg.transmission_stamp)).into_owned(),
        tf_data: tf2_msgs::msg::TFMessage::into_rmw_message(std::borrow::Cow::Owned(msg.tf_data)).into_owned(),
        map_in_flight: msg.map_in_flight,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      session_id: msg.session_id,
      sequence_id: msg.sequence_id,
        transmission_stamp: builtin_interfaces::msg::Time::into_rmw_message(std::borrow::Cow::Borrowed(&msg.transmission_stamp)).into_owned(),
        tf_data: tf2_msgs::msg::TFMessage::into_rmw_message(std::borrow::Cow::Borrowed(&msg.tf_data)).into_owned(),
      map_in_flight: msg.map_in_flight,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      session_id: msg.session_id,
      sequence_id: msg.sequence_id,
      transmission_stamp: builtin_interfaces::msg::Time::from_rmw_message(msg.transmission_stamp),
      tf_data: tf2_msgs::msg::TFMessage::from_rmw_message(msg.tf_data),
      map_in_flight: msg.map_in_flight,
    }
  }
}


// Corresponds to my_mesh_interfaces__msg__SenderStatus

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
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
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::SenderStatus::default())
  }
}

impl rosidl_runtime_rs::Message for SenderStatus {
  type RmwMsg = super::msg::rmw::SenderStatus;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        session_id: msg.session_id,
        last_sequence_sent: msg.last_sequence_sent,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      session_id: msg.session_id,
      last_sequence_sent: msg.last_sequence_sent,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      session_id: msg.session_id,
      last_sequence_sent: msg.last_sequence_sent,
    }
  }
}


