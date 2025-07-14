import { signal } from '@angular/core';
import { TokenCardComponent } from './token-card.component';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  NoopAnimationsModule,
  provideNoopAnimations,
} from '@angular/platform-browser/animations';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('TokenCardComponent', () => {
  let component: TokenCardComponent;
  let fixture: ComponentFixture<TokenCardComponent>;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenCardComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenCardComponent);
    component = fixture.componentInstance;
    component.selectedTabIndex = signal(0);
    component.selectedContent = signal('token_overview');
    component.tokenSerial = signal('Mock serial');
    component.containerSerial = signal('Mock container');
    component.states = signal([]);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('onTabChange()', () => {
    it('should do nothing except reset `isProgrammaticChange` when it is true', () => {
      component.isProgrammaticTabChange.set(true);
      component.selectedTabIndex.set(1);
      component.selectedContent.set('token_overview');
      component.containerSerial.set('Mock serial');
      component.tokenSerial.set('Mock serial');

      component.onTabChange();

      expect(component.selectedTabIndex()).toBe(1);
      expect(component.selectedContent()).toBe('token_overview');
      expect(component.containerSerial()).toBe('Mock serial');
      expect(component.tokenSerial()).toBe('Mock serial');
    });

    it('should set selectedContent to "token_overview" and clear serials if selectedTabIndex is 0', () => {
      component.isProgrammaticTabChange.set(false);
      component.selectedTabIndex.set(0);
      component.selectedContent.set('container_details');
      component.containerSerial.set('Mock serial');
      component.tokenSerial.set('Mock serial');

      component.onTabChange();

      expect(component.selectedContent()).toBe('token_overview');
      expect(component.containerSerial()).toBe('');
      expect(component.tokenSerial()).toBe('');
    });

    it('should set selectedContent to "container_overview" and clear serials if selectedTabIndex is 1', () => {
      component.isProgrammaticTabChange.set(false);
      component.selectedTabIndex.set(1);
      component.selectedContent.set('token_details');
      component.containerSerial.set('Mock serial');
      component.tokenSerial.set('Mock serial');

      component.onTabChange();

      expect(component.selectedContent()).toBe('container_overview');
      expect(component.containerSerial()).toBe('');
      expect(component.tokenSerial()).toBe('');
    });
  });
});
