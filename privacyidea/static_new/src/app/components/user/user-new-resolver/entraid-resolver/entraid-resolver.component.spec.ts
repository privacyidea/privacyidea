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
import { EntraidResolverComponent } from "./entraid-resolver.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ComponentRef } from "@angular/core";

describe("EntraidResolverComponent", () => {
  let component: EntraidResolverComponent;
  let componentRef: ComponentRef<EntraidResolverComponent>;
  let fixture: ComponentFixture<EntraidResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EntraidResolverComponent, NoopAnimationsModule]
    })
      .compileComponents();

    fixture = TestBed.createComponent(EntraidResolverComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize default data on creation", () => {
    componentRef.setInput("data", {});
    fixture.detectChanges();
    expect(component.baseUrlControl.value).toBe("https://graph.microsoft.com/v1.0");
    expect(component.authorityControl.value).toBe("https://login.microsoftonline.com/{tenant}");
    expect(component.configGetUserListGroup.value.endpoint).toBe("/users");
  });
});
