export const APP_META_UPDATED_EVENT = 'app:meta-updated'

export const defaultAppMeta = {
  app_title: 'React Go Admin',
  project_name: 'React Go Admin',
  app_description: 'React Go Admin Description',
  login_page_image_url: '',
  login_page_image_mode: 'contain',
  login_page_image_zoom: 1,
  login_page_image_position_x: 50,
  login_page_image_position_y: 50,
  notification_position: 'top-right',
  notification_duration: 4000,
  notification_visible_toasts: 3,
}

export const dispatchAppMetaUpdated = (payload = {}) => {
  window.dispatchEvent(new CustomEvent(APP_META_UPDATED_EVENT, { detail: payload }))
}
