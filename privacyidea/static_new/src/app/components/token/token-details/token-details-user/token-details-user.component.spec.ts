/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { TokenDetailsUserComponent } from "./token-details-user.component";
import { TokenService } from "../../../../services/token/token.service";
import { AppComponent } from "../../../../app.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { UserService } from "../../../../services/user/user.service";
import { MockUserService } from "../../../../../testing/mock-services";

describe("TokenDetailsUserComponent", () => {
  let component: TokenDetailsUserComponent;
  let fixture: ComponentFixture<TokenDetailsUserComponent>;
  let tokenService: TokenService;
  let userService: MockUserService;

  beforeEach(async () => {
    jest.clearAllMocks();

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        TokenDetailsUserComponent,
        AppComponent,
        BrowserAnimationsModule
      ],
      providers: [
        TokenService,
        { provide: UserService, useClass: MockUserService },
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    }).compileComponents();

    tokenService = TestBed.inject(TokenService);
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    fixture = TestBed.createComponent(TokenDetailsUserComponent);
    component = fixture.componentInstance;

    component.tokenSerial = signal("Mock serial");
    component.isEditingUser = signal(false);

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should assign user", () => {
    userService.selectedUsername.set("testUser");
    userService.selectedUserRealm.set("testRealm");

    const assignSpy = jest.spyOn(tokenService, "assignUser");

    component.saveUser();

    expect(assignSpy).toHaveBeenCalledWith({
      realm: "testRealm",
      tokenSerial: "Mock serial",
      username: ""
    });
  });
});
