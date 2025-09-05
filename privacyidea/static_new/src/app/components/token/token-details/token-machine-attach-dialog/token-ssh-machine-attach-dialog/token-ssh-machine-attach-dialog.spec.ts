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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TokenSshMachineAssignDialogComponent } from "./token-ssh-machine-attach-dialog";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";

describe("TokenSshMachineAssignDialogComponent", () => {
  let component: TokenSshMachineAssignDialogComponent;
  let fixture: ComponentFixture<TokenSshMachineAssignDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenSshMachineAssignDialogComponent, BrowserAnimationsModule, MatDialogModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: {} },
        {
          provide: MatDialogRef,
          useValue: {
            close: () => {}
          }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenSshMachineAssignDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
