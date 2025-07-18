import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { TokenDetailsInfoComponent } from './token-details-info.component';
import { signal } from '@angular/core';

describe('TokenDetailsInfoComponent', () => {
  let component: TokenDetailsInfoComponent;
  let fixture: ComponentFixture<TokenDetailsInfoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsInfoComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenDetailsInfoComponent);
    component = fixture.componentInstance;
    component.infoData = signal([]);
    component.detailData = signal([]);
    component.isAnyEditingOrRevoked = signal(false);
    component.isEditingInfo = signal(false);
    component.isEditingUser = signal(false);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
