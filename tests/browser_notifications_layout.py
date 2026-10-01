"""Rendered layout regression check against a running Mission Control host.

Run with Playwright and Chromium installed. Set NOTIFICATIONS_TEST_TOKEN to the
host token, NOTIFICATIONS_UI_TEST_URL for a custom route URL, and optionally
NOTIFICATIONS_BROWSER_EXECUTABLE for an existing Chromium executable.
Notification API data is intercepted; this test never marks real items as read.
"""
import json
import os
from typing import Any
from playwright.sync_api import sync_playwright, expect


GEOMETRY = """() => {
  const route = document.querySelector('.route-page-scroll');
  const wrapper = route.firstElementChild;
  const style = getComputedStyle(route);
  return {
    available: route.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
    wrapper: wrapper.getBoundingClientRect().width,
    card: route.querySelector('[role="button"]').getBoundingClientRect().width,
    scrollWidth: route.scrollWidth, clientWidth: route.clientWidth,
  };
}"""


def run():
    with sync_playwright() as playwright:
        options: dict[str, Any] = {'headless': True}
        if executable := os.environ.get('NOTIFICATIONS_BROWSER_EXECUTABLE'):
            options['executable_path'] = executable
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page()
            token = os.environ.get('NOTIFICATIONS_TEST_TOKEN', 'isolated-layout-test-token')
            page.add_init_script('localStorage.setItem("mission-control-token", ' + json.dumps(token) + ')')
            item = {'id': 'layout-fixture', 'title': 'Layout fixture', 'body': 'A notification preview uses the available route width.',
                    'type': 'cron.event', 'severity': 'info', 'source': {'kind': 'cron', 'id': 'fixture'},
                    'createdAt': '2026-01-01T00:00:00Z', 'readAt': '2026-01-01T00:00:00Z', 'payload': {}}
            payload = {'items': [item], 'total': 1, 'allCount': 1, 'readCount': 1,
                       'unreadCount': 0, 'actionableCount': 0, 'hasMore': False, 'nextOffset': None}
            def notifications(route):
                assert route.request.method == 'GET', 'Layout test must not mutate notifications'
                route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))
            page.route('**/api/local/notifications**', notifications)
            page.goto(os.environ.get('NOTIFICATIONS_UI_TEST_URL', 'http://127.0.0.1:5174/notifications'))
            expect(page.get_by_role('heading', name='Layout fixture', exact=True)).to_be_visible()
            for width, height in [(1921, 1228), (1024, 768), (390, 844)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.wait_for_function("() => innerWidth === " + str(width))
                geometry = page.evaluate(GEOMETRY)
                assert abs(geometry['wrapper'] - geometry['available']) <= 1, geometry
                assert abs(geometry['card'] - geometry['available']) <= 1, geometry
                assert geometry['scrollWidth'] <= geometry['clientWidth'] + 1, geometry
                print('PASS notifications full width:', width, geometry)
        finally:
            browser.close()


if __name__ == '__main__':
    run()
