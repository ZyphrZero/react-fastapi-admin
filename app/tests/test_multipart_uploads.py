"""Regression tests for the JSON-or-multipart profile and application-settings endpoints.

These exercise the handler functions directly with a fake request whose ``form()``
returns real Starlette ``UploadFile`` objects, covering the deferred-upload
(multipart) flow ported from the Go sibling project as well as the legacy JSON flow.
"""

import asyncio
import io
from unittest.mock import AsyncMock, patch

from starlette.datastructures import FormData, Headers, UploadFile

from app.api.v1.base.base import update_user_profile
from app.api.v1.system_settings.system_settings import update_application_settings


class _FakeRequest:
    def __init__(self, *, content_type, form=None, json_body=None, app=None):
        self.headers = Headers({"content-type": content_type})
        self._form = form if form is not None else FormData()
        self._json = json_body
        self.app = app

    async def form(self):
        return self._form

    async def json(self):
        return self._json


class _User:
    def __init__(self, is_superuser=False):
        self.is_superuser = is_superuser


def _image_upload(name="avatar.png"):
    return UploadFile(file=io.BytesIO(b"\x89PNG\r\n\x1a\n"), filename=name)


def test_update_profile_multipart_replace_uploads_avatar():
    upload = _image_upload()
    form = FormData(
        [
            ("nickname", "Alice"),
            ("email", "alice@example.com"),
            ("phone", "13800000000"),
            ("avatar_mode", "replace"),
            ("avatar_file", upload),
        ]
    )
    request = _FakeRequest(content_type="multipart/form-data; boundary=x", form=form)

    with (
        patch(
            "app.api.v1.base.base.upload_service.upload_avatar",
            new=AsyncMock(return_value={"url": "/static/avatar/new.webp"}),
        ) as upload_mock,
        patch("app.api.v1.base.base.auth_service.update_current_user_profile", new=AsyncMock()) as update_mock,
    ):
        asyncio.run(update_user_profile(request=request, current_user=_User()))

    upload_mock.assert_awaited_once()
    assert upload_mock.await_args.args[0] is upload
    update_mock.assert_awaited_once()
    payload = update_mock.await_args.args[1]
    assert payload.avatar == "/static/avatar/new.webp"
    assert payload.nickname == "Alice"
    assert payload.email == "alice@example.com"
    assert payload.phone == "13800000000"


def test_update_profile_multipart_remove_clears_avatar():
    form = FormData([("nickname", "Bob"), ("email", ""), ("phone", ""), ("avatar_mode", "remove")])
    request = _FakeRequest(content_type="multipart/form-data; boundary=x", form=form)

    with (
        patch("app.api.v1.base.base.upload_service.upload_avatar", new=AsyncMock()) as upload_mock,
        patch("app.api.v1.base.base.auth_service.update_current_user_profile", new=AsyncMock()) as update_mock,
    ):
        asyncio.run(update_user_profile(request=request, current_user=_User()))

    upload_mock.assert_not_awaited()
    payload = update_mock.await_args.args[1]
    assert payload.avatar == ""
    assert payload.nickname == "Bob"
    assert payload.email is None
    assert payload.phone is None


def test_update_profile_json_flow_still_supported():
    request = _FakeRequest(
        content_type="application/json",
        json_body={
            "nickname": "Carol",
            "avatar": "/static/existing.webp",
            "email": "carol@example.com",
            "phone": "13900000000",
        },
    )
    with (
        patch("app.api.v1.base.base.upload_service.upload_avatar", new=AsyncMock()) as upload_mock,
        patch("app.api.v1.base.base.auth_service.update_current_user_profile", new=AsyncMock()) as update_mock,
    ):
        asyncio.run(update_user_profile(request=request, current_user=_User()))

    upload_mock.assert_not_awaited()
    payload = update_mock.await_args.args[1]
    assert payload.avatar == "/static/existing.webp"
    assert payload.nickname == "Carol"


def test_update_application_settings_multipart_uploads_login_image():
    upload = _image_upload("login.png")
    form = FormData(
        [
            ("app_title", "My Admin"),
            ("project_name", "My Admin"),
            ("app_description", "Desc"),
            ("debug", "false"),
            ("login_page_image_url", ""),
            ("login_page_image_mode", "contain"),
            ("login_page_image_zoom", "1"),
            ("login_page_image_position_x", "50"),
            ("login_page_image_position_y", "50"),
            ("notification_position", "top-right"),
            ("notification_duration", "4000"),
            ("notification_visible_toasts", "3"),
            ("login_page_image_action", "replace"),
            ("login_page_image_file", upload),
        ]
    )
    request = _FakeRequest(content_type="multipart/form-data; boundary=x", form=form, app=None)

    with (
        patch(
            "app.api.v1.system_settings.system_settings.upload_service.upload_image",
            new=AsyncMock(return_value={"url": "/static/image/login.png"}),
        ) as upload_mock,
        patch(
            "app.api.v1.system_settings.system_settings.system_setting_service.update_application_settings",
            new=AsyncMock(return_value={}),
        ) as update_mock,
    ):
        asyncio.run(update_application_settings(request=request, current_user=_User(is_superuser=True)))

    upload_mock.assert_awaited_once()
    assert upload_mock.await_args.args[0] is upload
    update_mock.assert_awaited_once()
    payload = update_mock.await_args.args[0]
    assert payload.login_page_image_url == "/static/image/login.png"
    assert payload.app_title == "My Admin"
    assert payload.debug is False


def test_update_application_settings_multipart_remove_clears_login_image():
    form = FormData(
        [
            ("app_title", "My Admin"),
            ("project_name", "My Admin"),
            ("app_description", "Desc"),
            ("debug", "false"),
            ("login_page_image_url", "/static/image/old.png"),
            ("login_page_image_mode", "contain"),
            ("login_page_image_zoom", "1"),
            ("login_page_image_position_x", "50"),
            ("login_page_image_position_y", "50"),
            ("notification_position", "top-right"),
            ("notification_duration", "4000"),
            ("notification_visible_toasts", "3"),
            ("login_page_image_action", "remove"),
        ]
    )
    request = _FakeRequest(content_type="multipart/form-data; boundary=x", form=form, app=None)

    with (
        patch(
            "app.api.v1.system_settings.system_settings.upload_service.upload_image", new=AsyncMock()
        ) as upload_mock,
        patch(
            "app.api.v1.system_settings.system_settings.system_setting_service.update_application_settings",
            new=AsyncMock(return_value={}),
        ) as update_mock,
    ):
        asyncio.run(update_application_settings(request=request, current_user=_User(is_superuser=True)))

    upload_mock.assert_not_awaited()
    payload = update_mock.await_args.args[0]
    assert payload.login_page_image_url == ""
