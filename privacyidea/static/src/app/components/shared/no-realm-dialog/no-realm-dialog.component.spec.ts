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
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { NoRealmDialogComponent, NoRealmDialogData } from "./no-realm-dialog.component";

describe("NoRealmDialogComponent", () => {
  let fixture: ComponentFixture<NoRealmDialogComponent>;
  let dialogRefMock: { close: jest.Mock };
  let routerMock: { navigateByUrl: jest.Mock };

  const button = (label: string): HTMLElement | undefined =>
    (Array.from(fixture.nativeElement.querySelectorAll(".pi-dialog-footer button")) as HTMLElement[]).find((b) =>
      b.textContent!.includes(label)
    );

  const setup = (data: NoRealmDialogData | null): void => {
    dialogRefMock = { close: jest.fn() };
    routerMock = { navigateByUrl: jest.fn().mockResolvedValue(true) };
    TestBed.configureTestingModule({
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: data },
        { provide: Router, useValue: routerMock }
      ]
    });
    fixture = TestBed.createComponent(NoRealmDialogComponent);
    fixture.detectChanges();
  };

  describe.each<{
    name: string;
    data: NoRealmDialogData;
    heading: string;
    text: string;
    primary: string;
    route: string;
  }>([
    {
      name: "with a resolver",
      data: { noResolver: false },
      heading: "No realm exists yet",
      text: "needed to enroll tokens",
      primary: "Create realm",
      route: ROUTE_PATHS.USERS_REALMS
    },
    {
      name: "without a resolver",
      data: { noResolver: true },
      heading: "No resolver",
      text: "Create a resolver first",
      primary: "Create resolver",
      route: ROUTE_PATHS.USERS_RESOLVERS_NEW
    }
  ])("$name", ({ data, heading, text, primary, route }) => {
    beforeEach(() => setup(data));

    it("shows heading and explanation", () => {
      expect(fixture.nativeElement.querySelector(".pi-dialog-header").textContent).toContain(heading);
      expect(fixture.nativeElement.textContent).toContain(text);
      if (data.noResolver) expect(button("Create realm")).toBeUndefined();
    });

    it(`navigates and closes on ${primary}`, () => {
      button(primary)!.click();
      expect(routerMock.navigateByUrl).toHaveBeenCalledWith(route);
      expect(dialogRefMock.close).toHaveBeenCalled();
    });

    it("only closes on Later", () => {
      button("Later")!.click();
      expect(routerMock.navigateByUrl).not.toHaveBeenCalled();
      expect(dialogRefMock.close).toHaveBeenCalled();
    });
  });
});
