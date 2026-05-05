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

import { NO_ERRORS_SCHEMA } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { ContentService } from "src/app/services/content/content.service";
import { MockContentService } from "src/testing/mock-services/mock-content-service";
import {
  ContainerTokensEnrolledDialogComponent,
  ContainerTokensEnrolledDialogData
} from "./container-tokens-enrolled-dialog.component";

const dialogClose = jest.fn();
const dialogRefMock = { close: dialogClose };

const makeToken = (serial: string, type: string) => ({
  serial,
  type,
  googleurl: { img: "img", value: "url", description: "" }
});

const threeTokens: ContainerTokensEnrolledDialogData = {
  containerSerial: "CONT-001",
  enrolledTokens: [makeToken("TOK-1", "hotp"), makeToken("TOK-2", "totp"), makeToken("TOK-3", "daypassword")]
};

describe("ContainerTokensEnrolledDialogComponent", () => {
  let component: ContainerTokensEnrolledDialogComponent;
  let fixture: ComponentFixture<ContainerTokensEnrolledDialogComponent>;
  let contentService: MockContentService;

  beforeEach(async () => {
    jest.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [ContainerTokensEnrolledDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: threeTokens },
        { provide: ContentService, useClass: MockContentService }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTokensEnrolledDialogComponent);
    component = fixture.componentInstance;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("starts on first token with correct total and progress", () => {
    expect(component.currentIndex()).toBe(0);
    expect(component.total()).toBe(3);
    expect(component.isFirst()).toBe(true);
    expect(component.isLast()).toBe(false);
    expect(component.progress()).toBeCloseTo(33.3, 0);
  });

  it("next() advances to second token", () => {
    component.next();
    expect(component.currentIndex()).toBe(1);
    expect(component.isFirst()).toBe(false);
    expect(component.isLast()).toBe(false);
  });

  it("previous() goes back from second to first token", () => {
    component.next();
    component.previous();
    expect(component.currentIndex()).toBe(0);
    expect(component.isFirst()).toBe(true);
  });

  it("next() does not advance past last token", () => {
    component.next();
    component.next();
    component.next();
    expect(component.currentIndex()).toBe(2);
    expect(component.isLast()).toBe(true);
  });

  it("previous() does not go before first token", () => {
    component.previous();
    expect(component.currentIndex()).toBe(0);
  });

  it("isLast() is true on last token and progress is 100%", () => {
    component.next();
    component.next();
    expect(component.isLast()).toBe(true);
    expect(component.progress()).toBe(100);
  });

  it("dialogActions: Previous button is disabled on first token", () => {
    const prev = component.dialogActions().find((a) => a.value === "previous")!;
    expect(prev.disabled).toBe(true);
  });

  it("dialogActions: Previous button is enabled after first token", () => {
    component.next();
    const prev = component.dialogActions().find((a) => a.value === "previous")!;
    expect(prev.disabled).toBe(false);
  });

  it("dialogActions: shows Next action when not on last token", () => {
    const hasNext = component.dialogActions().some((a) => a.value === "next");
    const hasFinish = component.dialogActions().some((a) => a.value === "finish");
    expect(hasNext).toBe(true);
    expect(hasFinish).toBe(false);
  });

  it("dialogActions: shows Finish action on last token", () => {
    component.next();
    component.next();
    const hasNext = component.dialogActions().some((a) => a.value === "next");
    const hasFinish = component.dialogActions().some((a) => a.value === "finish");
    expect(hasNext).toBe(false);
    expect(hasFinish).toBe(true);
  });

  it("onDialogAction('next') advances index", () => {
    component.onDialogAction("next");
    expect(component.currentIndex()).toBe(1);
  });

  it("onDialogAction('previous') decrements index", () => {
    component.next();
    component.onDialogAction("previous");
    expect(component.currentIndex()).toBe(0);
  });

  it("onDialogAction('finish') closes dialog and navigates to container details", () => {
    component.onDialogAction("finish");
    expect(dialogClose).toHaveBeenCalled();
    expect(contentService.navigateContainerDetails).toHaveBeenCalledWith("CONT-001");
  });

  it("finish() closes dialog and navigates to container details", () => {
    component.finish();
    expect(dialogClose).toHaveBeenCalled();
    expect(contentService.navigateContainerDetails).toHaveBeenCalledWith("CONT-001");
  });
});
