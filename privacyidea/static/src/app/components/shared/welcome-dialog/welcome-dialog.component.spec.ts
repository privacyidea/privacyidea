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
import { WelcomeDialogComponent } from "./welcome-dialog.component";

describe("WelcomeDialogComponent", () => {
  let fixture: ComponentFixture<WelcomeDialogComponent>;
  let component: WelcomeDialogComponent;
  let dialogRefMock: { close: jest.Mock };

  const heading = (): string => fixture.nativeElement.querySelector(".pi-dialog-header").textContent.trim();
  const buttons = (): HTMLElement[] => Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button"));
  const buttonLabels = (): string[] => buttons().map((button) => button.textContent!.trim());
  const clickButton = (label: string): void => {
    const button = buttons().find((candidate) => candidate.textContent!.includes(label));
    expect(button).toBeDefined();
    button!.click();
    fixture.detectChanges();
  };

  beforeEach(() => {
    dialogRefMock = { close: jest.fn() };

    TestBed.configureTestingModule({
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: null }
      ]
    });

    fixture = TestBed.createComponent(WelcomeDialogComponent);
    component = fixture.componentInstance;
  });

  it("should start at step 0 by default", () => {
    expect(component.step()).toBe(0);
  });

  it("nextWelcome should increment step and close after step 3", () => {
    component.nextWelcome();
    expect(component.step()).toBe(1);
    component.nextWelcome();
    expect(component.step()).toBe(2);
    component.nextWelcome();
    expect(component.step()).toBe(3);
    expect(dialogRefMock.close).not.toHaveBeenCalled();

    component.nextWelcome();
    expect(dialogRefMock.close).toHaveBeenCalled();
  });

  it("renders the step heading and its buttons in the shared dialog wrapper", () => {
    fixture.detectChanges();

    expect(heading()).toBe("Welcome");
    expect(buttonLabels()).toHaveLength(1);
    expect(buttonLabels()[0]).toContain("Next");

    component.step.set(3);
    fixture.detectChanges();

    expect(heading()).toBe("Thank you for improving your security!");
    expect(buttonLabels()).toHaveLength(2);
    expect(buttonLabels()[0]).toContain("Read Again");
    expect(buttonLabels()[1]).toContain("Dive In!");
  });

  it("gives the open source and enterprise steps their own headings", () => {
    component.step.set(1);
    fixture.detectChanges();
    expect(heading()).toBe("The Value of Open Source");

    component.step.set(2);
    fixture.detectChanges();
    expect(heading()).toBe("The Added Value of privacyIDEA Enterprise Edition");
    expect(buttonLabels()).toHaveLength(1);
    expect(buttonLabels()[0]).toContain("Next");
  });

  it("restarts on the read again action and advances on every other action", () => {
    component.step.set(3);
    fixture.detectChanges();

    clickButton("Read Again");
    expect(component.step()).toBe(0);

    clickButton("Next");
    expect(component.step()).toBe(1);
  });

  it("resetWelcome should set step back to 0", () => {
    component.step.set(3);
    component.resetWelcome();
    expect(component.step()).toBe(0);
  });
});
