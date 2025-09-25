import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TokenHotpMachineAssignDialogComponent } from "./token-hotp-machine-attach-dialog";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";

describe("TokenHotpMachineAssignDialogComponent", () => {
  let component: TokenHotpMachineAssignDialogComponent;
  let fixture: ComponentFixture<TokenHotpMachineAssignDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenHotpMachineAssignDialogComponent, BrowserAnimationsModule, MatDialogModule],
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

    fixture = TestBed.createComponent(TokenHotpMachineAssignDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
