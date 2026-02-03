/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export class MockVersioningService {
  version = { set: jest.fn() } as any;
}
