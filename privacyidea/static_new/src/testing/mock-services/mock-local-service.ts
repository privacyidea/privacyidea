/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { LocalServiceInterface } from "../../app/services/local/local.service";

export class MockLocalService implements LocalServiceInterface {
  private data: Record<string, string> = {};
  key: string = "mockLocalServiceKey";
  saveData = jest.fn().mockImplementation((key: string, value: string) => {
    this.data[key] = value;
  });
  getData = jest.fn().mockImplementation((key: string) => {
    const dataValue = this.data[key];
    if (dataValue === undefined) {
      console.warn(`MockLocalService: No data found for key: ${key}`);
      return "";
    }
    return dataValue;
  });
  removeData = jest.fn().mockImplementation((key: string) => {
    if (this.data[key] !== undefined) {
      delete this.data[key];
    } else {
      console.warn(`MockLocalService: No data found for key: ${key}`);
    }
  });
}
