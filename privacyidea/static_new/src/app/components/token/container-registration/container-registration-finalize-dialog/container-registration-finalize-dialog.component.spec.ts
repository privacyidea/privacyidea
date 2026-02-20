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
import { ContainerRegistrationFinalizeDialogComponent } from "./container-registration-finalize-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { By } from "@angular/platform-browser";
import { NO_ERRORS_SCHEMA, signal } from "@angular/core";
import { provideHttpClient } from "@angular/common/http";
import { MockMatDialogRef } from "../../../../../testing/mock-mat-dialog-ref";

const detectChangesStable = async (fixture: ComponentFixture<any>) => {
  fixture.detectChanges();
  await Promise.resolve();
  fixture.detectChanges();
};

describe("ContainerRegistrationFinalizeDialogComponent", () => {
  let component: ContainerRegistrationFinalizeDialogComponent;
  let fixture: ComponentFixture<ContainerRegistrationFinalizeDialogComponent>;
  let mockRegisterContainer: jest.Mock;

  const mockData = signal({
    rollover: false,
    response: {
      result: {
        value: {
          container_url: {
            img: "test-img-url",
            value: "test-link"
          }
        }
      }
    },
    registerContainer: jest.fn()
  });

  beforeEach(async () => {
    await TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerRegistrationFinalizeDialogComponent],
      providers: [
        provideHttpClient(),
        { provide: MAT_DIALOG_DATA, useValue: mockData },
        { provide: MatDialogRef, useClass: MockMatDialogRef }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerRegistrationFinalizeDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    mockRegisterContainer = mockData().registerContainer;
  });

  it("should create", () => {
    expect(component).toBeDefined();
  });

  it("should render 'Register Container' title when not rollover", () => {
    const title = fixture.nativeElement.querySelector("h2");
    expect(title.textContent).toContain("Register Container");
  });

  it("should render 'Container Rollover' title when rollover is true", async () => {
    const rolloverData = signal({ ...mockData(), rollover: true });
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerRegistrationFinalizeDialogComponent],
      providers: [
        provideHttpClient(),
        { provide: MAT_DIALOG_DATA, useValue: rolloverData },
        { provide: MatDialogRef, useClass: MockMatDialogRef }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(ContainerRegistrationFinalizeDialogComponent);
    component = fixture.componentInstance;
    await detectChangesStable(fixture);
    const titles = fixture.nativeElement.querySelectorAll("h2");
    const titleText = Array.from(titles)
      .map((el: any) => el.textContent.trim())
      .join(" ");
    expect(titleText).toContain("Container Rollover");
  });

  it("should display QR code image if present", () => {
    const img = fixture.nativeElement.querySelector("img.qr-code");
    expect(img).not.toBeNull();
    expect(img.src).toContain("test-img-url");
  });

  it("should display registration link", () => {
    const link = fixture.nativeElement.querySelector("a");
    expect(link).not.toBeNull();
    expect(link.href).toContain("test-link");
  });

  it("should call registerContainer with correct arguments when regenerateQRCode is called", () => {
    component.regenerateQRCode();
    expect(mockRegisterContainer).toHaveBeenCalledWith(undefined, undefined, undefined, false, true);
  });

  it("should call regenerateQRCode when button is clicked", () => {
    const button = fixture.debugElement.query(By.css("button.action-button-1"));
    button.triggerEventHandler("click");
    expect(mockRegisterContainer).toHaveBeenCalled();
  });
});
