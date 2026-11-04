/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";

import { ContentService } from "@services/content/content.service";
import { MockContentService } from "@testing/mock-services";
import { FindSerialResultDialogComponent, GetSerialResultDialogData } from "./find-serial-result-dialog.component";

describe("GetSerialResultDialogComponent", () => {
  let component: FindSerialResultDialogComponent;
  let fixture: ComponentFixture<FindSerialResultDialogComponent>;

  const mockDialogRef = { close: jest.fn() };

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [FindSerialResultDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            serialList: ["Mock serial"]
          } as unknown as GetSerialResultDialogData
        },
        { provide: ContentService, useClass: MockContentService },
        {
          provide: MatDialogRef,
          useValue: mockDialogRef
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(FindSerialResultDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("onClickSerial opens the found token through the content service", () => {
    component.data.foundSerial = "A#1";
    component.onClickSerial();
    expect((component.contentService as unknown as MockContentService).tokenSelected).toHaveBeenCalledWith("A#1");
  });

  it("should call dialogRef.close() when you invoke close()", () => {
    component.dialogRef.close("reset");
    expect(mockDialogRef.close).toHaveBeenCalledWith("reset");
  });
});
