import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  BrowserAnimationsModule,
  provideNoopAnimations,
} from '@angular/platform-browser/animations';
import { TokenComponent } from './token.component';
import { OverflowService } from '../../services/overflow/overflow.service';
import { MockOverflowService } from '../../../testing/mock-services';

describe('TokenComponent', () => {
  let component: TokenComponent;
  let fixture: ComponentFixture<TokenComponent>;
  let mockOverflowService: MockOverflowService;

  beforeEach(async () => {
    mockOverflowService = new MockOverflowService();
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [BrowserAnimationsModule, TokenComponent],
      providers: [
        { provide: OverflowService, useValue: mockOverflowService },
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show token card outside the drawer if overflowService returns false', () => {
    mockOverflowService.setWidthOverflow(false);
    fixture.detectChanges();

    const cardOutsideDrawer = fixture.nativeElement.querySelector(
      'app-token-card.margin-right-1',
    );
    const drawer = fixture.nativeElement.querySelector('mat-drawer');

    expect(cardOutsideDrawer).toBeTruthy();
    expect(drawer).toBeNull();
  });

  it('should show token card in drawer if overflowService returns true', () => {
    mockOverflowService.setWidthOverflow(true);
    fixture.detectChanges();

    const cardOutsideDrawer = fixture.nativeElement.querySelector(
      'app-token-card.margin-right-1',
    );
    const drawer = fixture.nativeElement.querySelector('mat-drawer');

    expect(cardOutsideDrawer).toBeNull();
    expect(drawer).toBeTruthy();
  });
});
