import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { TokenGetSerialComponent } from "./token-get-serial.component";

describe("TokenGetSerial", () => {
  let component: TokenGetSerialComponent;
  let fixture: ComponentFixture<TokenGetSerialComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenGetSerialComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenGetSerialComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
