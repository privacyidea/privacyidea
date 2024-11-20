import {ComponentFixture, TestBed} from '@angular/core/testing';

import {GridLayoutComponent} from './grid-layout.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {ActivatedRoute} from '@angular/router';
import {of} from 'rxjs';

describe('GridLayoutComponent', () => {
  let component: GridLayoutComponent;
  let fixture: ComponentFixture<GridLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GridLayoutComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), [
        {
          provide: ActivatedRoute,
          useValue: {
            // Mock the necessary parts of ActivatedRoute, like params, queryParams, etc.
            params: of({id: '123'})
          }
        }
      ]],
    }).compileComponents();
    fixture = TestBed.createComponent(GridLayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
